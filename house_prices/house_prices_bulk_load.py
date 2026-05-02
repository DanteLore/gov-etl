"""
Bulk-load Land Registry Price Paid Data (PPD) into S3.

Downloads yearly CSV files from the Land Registry, converts to Parquet
partitioned by year, and registers Glue partitions.

The PPD CSV files have no headers — columns are in a fixed order per the
Land Registry schema: https://www.gov.uk/guidance/about-the-price-paid-data

Usage:
    python house_prices/house_prices_bulk_load.py --start 2010
    python house_prices/house_prices_bulk_load.py --start 2010 --end 2024
    python house_prices/house_prices_bulk_load.py --start 2024 --end 2024
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition_y

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"

BASE_URL = "https://price-paid-data.publicdata.landregistry.gov.uk"

COLUMNS = [
    "transaction_id",
    "price",
    "date_of_transfer",
    "postcode",
    "property_type",
    "old_new",
    "duration",
    "paon",
    "saon",
    "street",
    "locality",
    "town_city",
    "district",
    "county",
    "ppd_category_type",
    "record_status",
]

TMP_PARQUET = "/tmp/house_prices.parquet"


def download_year(year: int) -> pd.DataFrame:
    url = f"{BASE_URL}/pp-{year}.csv"
    print(f"Downloading {url}")
    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()

    df = pd.read_csv(
        pd.io.common.BytesIO(response.content),
        header=None,
        names=COLUMNS,
        dtype=str,
        low_memory=False,
    )
    print(f"  {len(df):,} rows")
    return df


def upload_year(df: pd.DataFrame, year: int):
    df = df.copy()
    df["price"] = pd.to_numeric(df["price"], errors="coerce").astype("Int64")

    df.to_parquet(TMP_PARQUET, index=False)

    s3_key = f"house_prices/ppd/year={year}/ppd_{year}.parquet"
    load_file_to_s3(TMP_PARQUET, S3_INCOMING_BUCKET, s3_key)
    add_glue_partition_y(year, "house_prices_ppd", ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
    print(f"Uploaded year {year}: {len(df):,} rows")


def bulk_load(start_year: int, end_year: int):
    for year in range(start_year, end_year + 1):
        df = download_year(year)
        upload_year(df, year)

    print(f"Done. Loaded {end_year - start_year + 1} year(s).")


if __name__ == "__main__":
    current_year = datetime.now().year
    parser = argparse.ArgumentParser(description="Bulk load Land Registry Price Paid Data into S3")
    parser.add_argument("--start", type=int, required=True, help="Start year e.g. 2010")
    parser.add_argument("--end", type=int, default=current_year, help=f"End year (default: {current_year})")
    args = parser.parse_args()

    bulk_load(args.start, args.end)
