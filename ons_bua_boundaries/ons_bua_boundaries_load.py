"""
Load ONS Built-up Area (BUA) 2024 boundaries into S3 as Parquet.

Fetches all 7,775 polygon boundaries from the ArcGIS REST API, paging through
the 2,000-record limit, and stores per feature:
  - geometry_wgs84_wkt   — original WGS84 (EPSG:4326) polygon as WKT
  - geometry_osgb_wkt    — reprojected to British National Grid (EPSG:27700) as WKT
  - centre_e / centre_n  — OSGB centroid (easting/northing)
  - bbox_min_e / bbox_min_n / bbox_max_e / bbox_max_n — OSGB bounding rectangle

No partitioning — this is a small static reference dataset.

Usage:
    python ons_bua_boundaries/ons_bua_boundaries_load.py
"""

import sys
import tempfile
from pathlib import Path

import pandas as pd
import requests
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3

S3_INCOMING_BUCKET = "dantelore.data.incoming"
S3_KEY = "ons_bua_boundaries/bua/bua_2024.parquet"

ARCGIS_URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/ArcGIS/rest/services"
    "/main_ONS_BUA_2024_EW_V2/FeatureServer/0/query"
)

PAGE_SIZE = 2000

# WGS84 → British National Grid, always_xy so coords are (lng, lat) → (E, N)
_to_osgb = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True).transform


def fetch_all_features() -> list[dict]:
    features = []
    offset = 0
    while True:
        params = {
            "where": "1=1",
            "outFields": "BUA24CD,BUA24NM",
            "outSR": "4326",
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
            "f": "geojson",
        }
        response = requests.get(ARCGIS_URL, params=params, timeout=120)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(f"ArcGIS error: {data['error']}")
        page = data.get("features", [])
        features.extend(page)
        print(f"  Fetched {len(features)} features...")
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return features


def process_feature(f: dict) -> dict:
    props = f["properties"]
    geom_wgs84 = shape(f["geometry"])
    geom_osgb = transform(_to_osgb, geom_wgs84)

    centroid = geom_osgb.centroid
    minx, miny, maxx, maxy = geom_osgb.bounds

    return {
        "bua24cd": props["BUA24CD"],
        "bua24nm": props["BUA24NM"],
        "geometry_wgs84_wkt": geom_wgs84.wkt,
        "geometry_osgb_wkt": geom_osgb.wkt,
        "centre_e": round(centroid.x),
        "centre_n": round(centroid.y),
        "bbox_min_e": round(minx),
        "bbox_min_n": round(miny),
        "bbox_max_e": round(maxx),
        "bbox_max_n": round(maxy),
    }


def load():
    print("Fetching all BUA 2024 boundaries...")
    features = fetch_all_features()
    print(f"  Total: {len(features)} features")

    print("Processing geometries...")
    rows = [process_feature(f) for f in features]

    df = pd.DataFrame(rows, columns=[
        "bua24cd", "bua24nm",
        "geometry_wgs84_wkt", "geometry_osgb_wkt",
        "centre_e", "centre_n",
        "bbox_min_e", "bbox_min_n", "bbox_max_e", "bbox_max_n",
    ])

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name

    df.to_parquet(tmp_path, index=False)
    load_file_to_s3(tmp_path, S3_INCOMING_BUCKET, S3_KEY)
    print("Done.")


if __name__ == "__main__":
    load()
