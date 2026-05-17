"""
Load ONS Counties and Unitary Authorities (CTYUA) boundaries into S3 as Parquet.

Source: CTYUA_Apr_2019_UGCB_Great_Britain_2022 ArcGIS FeatureServer (Ultra Generalised
Clipped Boundaries). The full-resolution NC services exceed the ArcGIS transfer limit per
feature and cannot be paginated with geometry. The UGCB variant is suitable for spatial
filtering, bbox lookups and display — not for precise boundary measurements.

Boundary vintage is April 2019 but area codes are stable and match current ONS codes
(e.g. West Berkshire = E06000037). 205 areas covering England, Wales and Scotland.

The service already provides OSGB centroid (bng_e / bng_n) and WGS84 centre (long / lat).
We reproject geometry to OSGB and compute the bounding rectangle ourselves for consistency
with the BUA boundaries table.

No partitioning — small static reference dataset.

Usage:
    python ons_ctyua_boundaries/ons_ctyua_boundaries_load.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.arcgis import fetch_and_build_dataframe, geometry_columns
from helpers.aws import load_file_to_s3

S3_INCOMING_BUCKET = "dantelore.data.incoming"
S3_KEY = "ons_ctyua_boundaries/ctyua/ctyua_2025.parquet"

# Ultra Generalised Clipped Boundaries — small enough to page with geometry
ARCGIS_URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/ArcGIS/rest/services"
    "/CTYUA_Apr_2019_UGCB_Great_Britain_2022/FeatureServer/0/query"
)

COLUMNS = [
    "ctyua25cd", "ctyua25nm", "ctyua25nmw",
    "geometry_wgs84_wkt", "geometry_osgb_wkt",
    "centre_e", "centre_n",
    "bbox_min_e", "bbox_min_n", "bbox_max_e", "bbox_max_n",
]


def process_feature(f: dict) -> dict:
    props = f["properties"]
    welsh = props.get("ctyua19nmw", "").strip() or None
    return {
        "ctyua25cd": props["ctyua19cd"],
        "ctyua25nm": props["ctyua19nm"],
        "ctyua25nmw": welsh,
        **geometry_columns(f),
    }


def load():
    print("Fetching all CTYUA boundaries...")
    df = fetch_and_build_dataframe(
        ARCGIS_URL,
        "ctyua19cd,ctyua19nm,ctyua19nmw",
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
