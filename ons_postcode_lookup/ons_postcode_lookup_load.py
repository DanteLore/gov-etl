"""
Load ONS Postcode to MSOA/LAD/CTYUA/RGN/CTRY Best Fit Lookup into S3, partitioned by
postcode area (e.g. 'rg', 'sw').

Source: ArcGIS FeatureServer — Postcode_to_OA_(2021)_to_LSOA_to_MSOA_to_LAD_to_CTYUA_
to_RGN_to_CTRY_Best_Fit_Lookup_in_EW. ~2.35M postcodes in England and Wales.

The service caps pages at 1,000 records. Concurrent requests are used to fetch all
pages quickly.

Usage:
    python ons_postcode_lookup/ons_postcode_lookup_load.py
"""

import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import add_glue_partition_area, load_file_to_s3

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"

ARCGIS_URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/ArcGIS/rest/services"
    "/Postcode_to_OA_(2021)_to_LSOA_to_MSOA_to_LAD_to_CTYUA_to_RGN_to_CTRY_Best_Fit_Lookup_in_EW"
    "/FeatureServer/0/query"
)

OUT_FIELDS = "pcd,msoa21cd,msoa21nm,lad22cd,lad22nm,ctyua22cd,ctyua22nm,rgn22cd,rgn22nm,ctry22cd,ctry22nm"

PAGE_SIZE = 1000
MAX_WORKERS = 8
MAX_RETRIES = 5

COLUMNS = [
    "postcode", "postcode_area",
    "msoa21cd", "msoa21nm",
    "lad22cd", "lad22nm",
    "ctyua22cd", "ctyua22nm",
    "rgn22cd", "rgn22nm",
    "ctry22cd", "ctry22nm",
]


def fetch_count() -> int:
    r = requests.get(ARCGIS_URL, params={"where": "1=1", "returnCountOnly": "true", "f": "json"}, timeout=30)
    r.raise_for_status()
    return r.json()["count"]


def fetch_page(offset: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": OUT_FIELDS,
        "returnGeometry": "false",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "f": "json",
    }
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(ARCGIS_URL, params=params, timeout=60)
            r.raise_for_status()
            return [f["attributes"] for f in r.json().get("features", [])]
        except requests.HTTPError as e:
            if attempt < MAX_RETRIES - 1 and e.response.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
            else:
                raise


def postcode_area(pcd: str) -> str:
    import re
    m = re.match(r"^([A-Za-z]+)", (pcd or "").strip())
    return m.group(1).lower() if m else "unknown"


def attrs_to_row(attrs: dict) -> dict:
    pcd = (attrs.get("pcd") or "").strip()
    return {
        "postcode": pcd,
        "postcode_area": postcode_area(pcd),
        "msoa21cd": attrs.get("msoa21cd"),
        "msoa21nm": attrs.get("msoa21nm"),
        "lad22cd": attrs.get("lad22cd"),
        "lad22nm": attrs.get("lad22nm"),
        "ctyua22cd": attrs.get("ctyua22cd"),
        "ctyua22nm": attrs.get("ctyua22nm"),
        "rgn22cd": attrs.get("rgn22cd"),
        "rgn22nm": attrs.get("rgn22nm"),
        "ctry22cd": attrs.get("ctry22cd"),
        "ctry22nm": attrs.get("ctry22nm"),
    }


def load():
    print("Counting records...")
    total = fetch_count()
    offsets = list(range(0, total, PAGE_SIZE))
    print(f"  {total:,} records, {len(offsets)} pages — fetching with {MAX_WORKERS} workers...")

    all_attrs = []
    completed = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_page, off): off for off in offsets}
        for future in as_completed(futures):
            all_attrs.extend(future.result())
            completed += 1
            if completed % 100 == 0:
                print(f"  {completed}/{len(offsets)} pages...")

    print(f"  {len(all_attrs):,} rows fetched — building DataFrame...")
    rows = [attrs_to_row(a) for a in all_attrs]
    df = pd.DataFrame(rows, columns=COLUMNS)

    areas = sorted(df["postcode_area"].unique())
    print(f"  {len(areas)} postcode areas — uploading...")

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name

    for area in areas:
        area_df = df[df["postcode_area"] == area].drop(columns=["postcode_area"])
        area_df.to_parquet(tmp_path, index=False)
        s3_key = f"ons_postcode_lookup/lookup/postcode_area={area}/lookup_{area}.parquet"
        load_file_to_s3(tmp_path, S3_INCOMING_BUCKET, s3_key)
        add_glue_partition_area(area, "ons_postcode_lookup_lookup", ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)

    print("Done.")


if __name__ == "__main__":
    load()
