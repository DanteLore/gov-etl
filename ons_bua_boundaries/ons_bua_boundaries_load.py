"""
Load ONS Built-up Area (BUA) 2024 boundaries into S3 as Parquet.

Fetches all 7,775 polygon boundaries from the ArcGIS REST API and stores per feature:
  - geometry_wgs84_wkt / geometry_osgb_wkt — polygon WKT in both projections
  - centre_e / centre_n — OSGB centroid
  - bbox_min_e / bbox_min_n / bbox_max_e / bbox_max_n — OSGB bounding rectangle

No partitioning — small static reference dataset.

Usage:
    python ons_bua_boundaries/ons_bua_boundaries_load.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.arcgis import fetch_and_build_dataframe, geometry_columns
from helpers.aws import load_file_to_s3

S3_INCOMING_BUCKET = "dantelore.data.incoming"
S3_KEY = "ons_bua_boundaries/bua/bua_2024.parquet"

ARCGIS_URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/ArcGIS/rest/services"
    "/main_ONS_BUA_2024_EW_V2/FeatureServer/0/query"
)

COLUMNS = [
    "bua24cd", "bua24nm",
    "geometry_wgs84_wkt", "geometry_osgb_wkt",
    "centre_e", "centre_n",
    "bbox_min_e", "bbox_min_n", "bbox_max_e", "bbox_max_n",
]


def process_feature(f: dict) -> dict:
    props = f["properties"]
    return {
        "bua24cd": props["BUA24CD"],
        "bua24nm": props["BUA24NM"],
        **geometry_columns(f),
    }


def load():
    print("Fetching all BUA 2024 boundaries...")
    df = fetch_and_build_dataframe(ARCGIS_URL, "BUA24CD,BUA24NM", process_feature, COLUMNS)

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name

    df.to_parquet(tmp_path, index=False)
    load_file_to_s3(tmp_path, S3_INCOMING_BUCKET, S3_KEY)
    print("Done.")


if __name__ == "__main__":
    load()
