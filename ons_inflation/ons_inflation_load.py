"""
Load ONS inflation time series into S3 as a single Parquet file.

Fetches monthly CPI, CPIH and RPI data from the ONS website for the MM23
dataset. All series are combined into one wide table with one row per
year/month.

Series loaded:
    l522  — CPI index (2015=100), from 1988
    d7g7  — CPI 12-month rate %, from 1989
    l55o  — CPIH index (2015=100), from 1988
    d7bt  — CPIH 12-month rate %, from 1989
    czbh  — RPI 12-month rate %, from 1948

Usage:
    python ons_inflation/ons_inflation_load.py
"""

import sys
import tempfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3

S3_INCOMING_BUCKET = "dantelore.data.incoming"
S3_KEY = "ons_inflation/inflation/inflation.parquet"

ONS_BASE = "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/{series}/mm23/data"

SERIES = {
    "l522": "cpi_index",
    "d7g7": "cpi_rate",
    "l55o": "cpih_index",
    "d7bt": "cpih_rate",
    "czbh": "rpi_rate",
}

MONTH_MAP = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}


def fetch_series(series_id: str) -> pd.DataFrame:
    url = ONS_BASE.format(series=series_id)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    months = response.json().get("months", [])
    rows = []
    for m in months:
        month_num = MONTH_MAP.get(m["month"])
        if month_num is None:
            continue
        value = None if m["value"] in ("", "-") else float(m["value"])
        rows.append({"year": int(m["year"]), "month": month_num, "value": value})
    return pd.DataFrame(rows)


def load():
    combined = None

    for series_id, col_name in SERIES.items():
        print(f"  Fetching {series_id} ({col_name})...")
        df = fetch_series(series_id).rename(columns={"value": col_name})
        combined = df if combined is None else combined.merge(df, on=["year", "month"], how="outer")

    combined = combined.sort_values(["year", "month"]).reset_index(drop=True)
    combined["year"] = combined["year"].astype("Int64")
    combined["month"] = combined["month"].astype("Int64")
    for col in SERIES.values():
        combined[col] = combined[col].astype("float64")

    print(f"  {len(combined):,} rows ({combined['year'].min()}-{combined['year'].max()})")

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name

    combined.to_parquet(tmp_path, index=False)
    load_file_to_s3(tmp_path, S3_INCOMING_BUCKET, S3_KEY)
    print("Done.")


if __name__ == "__main__":
    load()
