"""
Load NaPTAN (National Public Transport Access Nodes) into S3: every bus stop, station entrance, ferry and
tram stop in Great Britain, with its location.

Source: the NaPTAN API's full CSV download (about 436,000 stops, including inactive ones). Column names are
snake_cased from the source; Easting/Northing become x_coordinate/y_coordinate (OSGB36) and the table is
partitioned by 100km grid tile like the other gov-etl point datasets. A reload overwrites each tile.

Usage:
    python naptan_stops/naptan_stops_load.py
"""

import io
import re
import sys
import tempfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition_en

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"
TABLE = "naptan_stops"
URL = "https://naptan.api.dft.gov.uk/v1/access-nodes?dataFormat=csv"


def snake(name):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()


def load():
    print(f"Downloading {URL}...")
    r = requests.get(URL, timeout=600)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), dtype=str)
    df.columns = [snake(c) for c in df.columns]
    df = df.rename(columns={"atcocode": "atco_code", "easting": "x_coordinate", "northing": "y_coordinate"})
    df["x_coordinate"] = df["x_coordinate"].astype(int)
    df["y_coordinate"] = df["y_coordinate"].astype(int)
    df["longitude"] = df["longitude"].astype(float)
    df["latitude"] = df["latitude"].astype(float)
    for col in ["creation_date_time", "modification_date_time"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["locality_centre"] = df["locality_centre"].map({"true": True, "false": False})
    df["grid_e"] = df["x_coordinate"] // 100_000
    df["grid_n"] = df["y_coordinate"] // 100_000
    print(f"{len(df):,} stops")

    for (grid_e, grid_n), tile in df.groupby(["grid_e", "grid_n"]):
        with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
            tile.drop(columns=["grid_e", "grid_n"]).to_parquet(tmp.name, index=False)
            load_file_to_s3(tmp.name, S3_INCOMING_BUCKET, f"{TABLE}/grid_e={grid_e}/grid_n={grid_n}/{TABLE}.parquet")
        add_glue_partition_en(grid_e, grid_n, TABLE, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
        print(f"  grid_e={grid_e} grid_n={grid_n}: {len(tile):,} stops")
    return df


if __name__ == "__main__":
    load()
