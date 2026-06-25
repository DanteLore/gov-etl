"""
Bulk-load Frankfurter exchange rate data into S3.

Downloads daily exchange rates from the Frankfurter API (ECB reference rates),
converts to Parquet partitioned by year, and registers Glue partitions.

Rates are EUR-based (all rates expressed as units of currency per 1 EUR).
Data is available from 1999-01-04 onwards.

Usage:
    python exchange_rates/exchange_rates_bulk_load.py --start 1999
    python exchange_rates/exchange_rates_bulk_load.py --start 1999 --end 2024
    python exchange_rates/exchange_rates_bulk_load.py --start 2024 --end 2024
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

BASE_URL = "https://api.frankfurter.dev/v1"

TMP_PARQUET = "/tmp/exchange_rates.parquet"


def download_year(year: int) -> pd.DataFrame:
    url = f"{BASE_URL}/{year}-01-01..{year}-12-31"
    print(f"Downloading {url}")
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    data = response.json()
    base = data["base"]
    rates_by_date = data["rates"]

    rows = []
    for date_str, currency_rates in rates_by_date.items():
        for currency, rate in currency_rates.items():
            rows.append({
                "date": date_str,
                "base_currency": base,
                "currency": currency,
                "rate": rate,
            })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    print(f"  {len(df):,} rows ({df['currency'].nunique()} currencies, {df['date'].nunique()} trading days)")
    return df


def upload_year(df: pd.DataFrame, year: int):
    df.to_parquet(TMP_PARQUET, index=False)

    s3_key = f"exchange_rates/frankfurter/year={year}/exchange_rates_{year}.parquet"
    load_file_to_s3(TMP_PARQUET, S3_INCOMING_BUCKET, s3_key)
    add_glue_partition_y(year, "exchange_rates_frankfurter", ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
    print(f"Uploaded year {year}: {len(df):,} rows")


def bulk_load(start_year: int, end_year: int):
    for year in range(start_year, end_year + 1):
        df = download_year(year)
        upload_year(df, year)

    print(f"Done. Loaded {end_year - start_year + 1} year(s).")


if __name__ == "__main__":
    current_year = datetime.now().year
    parser = argparse.ArgumentParser(description="Bulk load Frankfurter exchange rate data into S3")
    parser.add_argument("--start", type=int, required=True, help="Start year e.g. 1999")
    parser.add_argument("--end", type=int, default=current_year, help=f"End year (default: {current_year})")
    args = parser.parse_args()

    bulk_load(args.start, args.end)
