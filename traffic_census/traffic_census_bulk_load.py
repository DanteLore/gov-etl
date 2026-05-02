"""
Bulk-load DfT AADF road traffic census data into S3.

Downloads the full AADF dataset from the DfT, converts to Parquet partitioned
by year, and registers Glue partitions.

Usage:
    python traffic_census/traffic_census_bulk_load.py
    python traffic_census/traffic_census_bulk_load.py --year 2023
"""

import argparse
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition_y

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"

AADF_URL = "https://storage.googleapis.com/dft-statistics/road-traffic/downloads/data-gov-uk/dft_traffic_counts_aadf.zip"

TMP_PARQUET = "/tmp/traffic_census.parquet"


def download_aadf() -> pd.DataFrame:
    print(f"Downloading AADF data from {AADF_URL}")
    response = requests.get(AADF_URL, stream=True, timeout=300)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        csv_names = [n for n in zf.namelist() if n.endswith('.csv')]
        if not csv_names:
            raise ValueError(f"No CSV found in zip. Contents: {zf.namelist()}")
        print(f"Reading {csv_names[0]} from zip")
        with zf.open(csv_names[0]) as f:
            df = pd.read_csv(f, low_memory=False)

    print(f"Downloaded {len(df):,} rows, years {df['year'].min()}–{df['year'].max()}")
    return df


def upload_year(df_year: pd.DataFrame, year: int):
    df_year = df_year.copy()
    df_year.columns = [c.lower().replace(' ', '_').replace('/', '_') for c in df_year.columns]

    df_year.to_parquet(TMP_PARQUET, index=False)

    s3_key = f"traffic_census/aadf/year={year}/aadf_{year}.parquet"
    load_file_to_s3(TMP_PARQUET, S3_INCOMING_BUCKET, s3_key)
    add_glue_partition_y(year, "traffic_census_aadf", ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
    print(f"Uploaded year {year}: {len(df_year):,} rows")


def bulk_load(year_filter=None):
    df = download_aadf()
    df.columns = [c.lower().replace(' ', '_').replace('/', '_') for c in df.columns]

    years = sorted(df['year'].unique())
    if year_filter:
        years = [y for y in years if y == year_filter]
        if not years:
            raise ValueError(f"Year {year_filter} not found in data")

    for year in years:
        upload_year(df[df['year'] == year], year)

    print(f"Done. Loaded {len(years)} year(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk load DfT AADF traffic census data into S3")
    parser.add_argument("--year", type=int, default=None, help="Load only this year (default: all years)")
    args = parser.parse_args()

    bulk_load(year_filter=args.year)
