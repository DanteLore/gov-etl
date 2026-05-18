"""
Load ONS MSOA 2021 boundaries into S3 as Parquet.

Fetches all 7,264 Middle Layer Super Output Area polygons from the ArcGIS REST API
(Super Generalised Clipped Boundaries, BSC) and stores per feature:
  - geometry_wgs84_wkt / geometry_osgb_wkt — polygon WKT in both projections
  - centre_e / centre_n — OSGB centroid
  - bbox_min_e / bbox_min_n / bbox_max_e / bbox_max_n — OSGB bounding rectangle
  - ruc21cd / ruc21nm — Rural-Urban Classification

Covers England and Wales only. No partitioning — small static reference dataset.

Usage:
    python ons_msoa_boundaries/ons_msoa_boundaries_load.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.arcgis import fetch_and_build_dataframe, geometry_columns
from helpers.aws import load_file_to_s3

S3_INCOMING_BUCKET = "dantelore.data.incoming"
S3_KEY = "ons_msoa_boundaries/msoa/msoa_2021.parquet"

ARCGIS_URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/ArcGIS/rest/services"
    "/MSOA_2021_EW_BSC_V3_RUC/FeatureServer/0/query"
)

COLUMNS = [
    "msoa21cd", "msoa21nm", "msoa21nmw",
    "ruc21cd", "ruc21nm",
    "geometry_wgs84_wkt", "geometry_osgb_wkt",
    "centre_e", "centre_n",
    "bbox_min_e", "bbox_min_n", "bbox_max_e", "bbox_max_n",
]


def process_feature(f: dict) -> dict:
    props = f["properties"]
    welsh = (props.get("MSOA21NMW") or "").strip() or None
    return {
        "msoa21cd": props["MSOA21CD"],
        "msoa21nm": props["MSOA21NM"],
        "msoa21nmw": welsh,
        "ruc21cd": props.get("RUC21CD"),
        "ruc21nm": props.get("RUC21NM"),
        **geometry_columns(f),
    }


def load():
    print("Fetching all MSOA 2021 boundaries...")
    df = fetch_and_build_dataframe(
        ARCGIS_URL,
        "MSOA21CD,MSOA21NM,MSOA21NMW,RUC21CD,RUC21NM",
        process_feature,
        COLUMNS,
    )
    print(f"  {len(df)} rows")

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name

    df.to_parquet(tmp_path, index=False)
    load_file_to_s3(tmp_path, S3_INCOMING_BUCKET, S3_KEY)
    print("Done.")


if __name__ == "__main__":
    load()
