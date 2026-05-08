"""
Load OS Open UPRN data into S3, partitioned by 100km OSGB grid tile.

Downloads the current release zip from the OS Data Hub (no authentication required),
extracts the CSV, derives grid_e and grid_n from the OSGB easting/northing coordinates,
and writes one Parquet file per tile to S3.

Partition keys:
    grid_e  -- floor(X_COORDINATE / 100000), i.e. 100km easting tile index (0-6)
    grid_n  -- floor(Y_COORDINATE / 100000), i.e. 100km northing tile index (0-12)

Usage:
    python os_open_uprn/os_open_uprn_load.py
"""

import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition_en

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"

API_URL = "https://api.os.uk/downloads/v1/products/OpenUPRN/downloads"
DOWNLOAD_URL = f"{API_URL}?area=GB&format=CSV&redirect"

TMP_PARQUET = "/tmp/os_open_uprn_tile.parquet"


def fetch_csv_bytes() -> bytes:
    print("Fetching current release info...")
    releases = requests.get(API_URL, timeout=30)
    releases.raise_for_status()
    filename = next(r["fileName"] for r in releases.json() if r["format"] == "CSV")
    print(f"  Current release: {filename}")

    print(f"Downloading {DOWNLOAD_URL}")
    response = requests.get(DOWNLOAD_URL, stream=True, timeout=600)
    response.raise_for_status()

    print("  Extracting CSV from zip...")
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
        return zf.read(csv_name)


def load():
    csv_bytes = fetch_csv_bytes()

    print("Parsing CSV...")
    df = pd.read_csv(
        io.BytesIO(csv_bytes),
        dtype={"UPRN": "Int64", "X_COORDINATE": float, "Y_COORDINATE": float, "LATITUDE": float, "LONGITUDE": float},
        low_memory=False,
    )
    df.columns = [c.lower() for c in df.columns]
    print(f"  {len(df):,} rows")

    df["grid_e"] = (df["x_coordinate"] / 100_000).astype(int)
    df["grid_n"] = (df["y_coordinate"] / 100_000).astype(int)

    tiles = df.groupby(["grid_e", "grid_n"])
    print(f"  {len(tiles)} tiles")

    for (grid_e, grid_n), tile_df in tiles:
        tile = tile_df.drop(columns=["grid_e", "grid_n"])
        tile.to_parquet(TMP_PARQUET, index=False)

        s3_key = f"os_open_uprn/uprn/grid_e={grid_e}/grid_n={grid_n}/uprn.parquet"
        load_file_to_s3(TMP_PARQUET, S3_INCOMING_BUCKET, s3_key)
        add_glue_partition_en(grid_e, grid_n, "os_open_uprn_uprn", ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
        print(f"  Tile grid_e={grid_e} grid_n={grid_n}: {len(tile):,} rows")

    print("Done.")


if __name__ == "__main__":
    load()
