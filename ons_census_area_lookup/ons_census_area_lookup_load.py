"""
Load the ONS lookups from 2011 Census areas to 2021 Census areas (output areas, LSOAs and MSOAs) into S3, so
2011 and 2021 Census results can be compared on the same areas.

Source: ONS Open Geography Portal, "OA (2011) to OA (2021) to LAD (2022) exact fit", "LSOA (2011) to LSOA (2021)
to LAD (2022)" and "MSOA (2011) to MSOA (2021) to LAD (2022)" lookups. England and Wales. One row per 2011/2021
pair, with the ONS change indicator. Partitioned by geography_level. Static: load once.

Usage:
    python ons_census_area_lookup/ons_census_area_lookup_load.py
"""

import sys
import tempfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"
TABLE = "ons_census_area_lookup_2011_2021"
SERVICE = "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/{name}/FeatureServer/0/query"

# geography_level -> (service, source fields for code_2011, name_2011, code_2021, name_2021, change indicator)
LOOKUPS = {
    "oa": ("OA11_OA21_LAD22_EW_LU_Exact_fit_V3", ["OA11CD", None, "OA21CD", None, "CHNGIND"]),
    "lsoa": ("LSOA11_LSOA21_LAD22_EW_LU_v5", ["LSOA11CD", "LSOA11NM", "LSOA21CD", "LSOA21NM", "CHGIND"]),
    "msoa": ("MSOA11_MSOA21_LAD22_EW_LU_v2", ["MSOA11CD", "MSOA11NM", "MSOA21CD", "MSOA21NM", "CHNGIND"]),
}
COLUMNS = ["code_2011", "name_2011", "code_2021", "name_2021", "change_indicator"]


def fetch(service, fields):
    rows, offset = [], 0
    out_fields = ",".join(f for f in fields + ["LAD22CD", "LAD22NM"] if f)
    while True:
        r = requests.get(SERVICE.format(name=service), timeout=120, params={
            "where": "1=1", "outFields": out_fields, "returnGeometry": "false", "orderByFields": "ObjectId",
            "resultOffset": offset, "resultRecordCount": 1000, "f": "json"})
        r.raise_for_status()
        page = [f["attributes"] for f in r.json()["features"]]
        rows.extend(page)
        if len(page) < 1000:
            break
        offset += len(page)
    df = pd.DataFrame(rows)
    out = pd.DataFrame({col: df[f] if f else None for col, f in zip(COLUMNS, fields)})
    out["lad22_code"], out["lad22_name"] = df["LAD22CD"], df["LAD22NM"]
    return out.astype("string")


def load():
    for level, (service, fields) in LOOKUPS.items():
        df = fetch(service, fields)
        with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
            df.to_parquet(tmp.name, index=False)
            load_file_to_s3(tmp.name, S3_INCOMING_BUCKET, f"{TABLE}/geography_level={level}/{TABLE}_{level}.parquet")
        add_glue_partition("geography_level", level, TABLE, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
        print(f"  {level}: {len(df):,} rows, changes {df.change_indicator.value_counts().to_dict()}")


if __name__ == "__main__":
    load()
