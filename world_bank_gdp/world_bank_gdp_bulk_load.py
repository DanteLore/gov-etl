"""
Bulk-load World Bank GDP indicator data into S3.

Downloads GDP indicators for all countries from the World Bank API,
converts to a single Parquet file, and uploads to S3.

Indicators loaded:
    NY.GDP.MKTP.CD    - GDP (current US$)
    NY.GDP.MKTP.KD    - GDP (constant 2015 US$)
    NY.GDP.MKTP.PP.CD - GDP, PPP (current international $)
    NY.GDP.PCAP.CD    - GDP per capita (current US$)

Data is available from 1960 onwards. Coverage varies by country and indicator.

Usage:
    python world_bank_gdp/world_bank_gdp_bulk_load.py
"""

import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3

S3_INCOMING_BUCKET = "dantelore.data.incoming"
S3_KEY = "world_bank_gdp/world_bank_gdp.parquet"

BASE_URL = "https://api.worldbank.org/v2"

INDICATORS = [
    "NY.GDP.MKTP.CD",
    "NY.GDP.MKTP.KD",
    "NY.GDP.MKTP.PP.CD",
    "NY.GDP.PCAP.CD",
]

TMP_PARQUET = "/tmp/world_bank_gdp.parquet"


def download_indicator(indicator: str) -> list:
    url = f"{BASE_URL}/country/all/indicator/{indicator}"
    params = {
        "format": "json",
        "per_page": 20000,
    }
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()
    total_pages = data[0]["pages"]
    rows = data[1] or []

    for page in range(2, total_pages + 1):
        response = requests.get(url, params={**params, "page": page}, timeout=60)
        response.raise_for_status()
        rows.extend(response.json()[1] or [])

    return rows


def download_all() -> pd.DataFrame:
    records = []
    for indicator in INDICATORS:
        print(f"Downloading {indicator}")
        rows = download_indicator(indicator)
        for row in rows:
            records.append({
                "country_code": row["countryiso3code"],
                "country_name": row["country"]["value"],
                "indicator_id": row["indicator"]["id"],
                "indicator_name": row["indicator"]["value"],
                "year": int(row["date"]),
                "value": float(row["value"]) if row["value"] is not None else None,
            })
        print(f"  {len(rows):,} rows")

    df = pd.DataFrame(records, columns=["country_code", "country_name", "indicator_id", "indicator_name", "year", "value"])
    non_null = df["value"].notna().sum()
    print(f"Total: {len(df):,} rows ({non_null:,} non-null)")
    return df


def upload(df: pd.DataFrame):
    df.to_parquet(TMP_PARQUET, index=False)
    load_file_to_s3(TMP_PARQUET, S3_INCOMING_BUCKET, S3_KEY)
    print(f"Uploaded {len(df):,} rows to s3://{S3_INCOMING_BUCKET}/{S3_KEY}")


if __name__ == "__main__":
    df = download_all()
    upload(df)
    print("Done.")
