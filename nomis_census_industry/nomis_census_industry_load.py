"""
Load Census 2021 industry (TS060) counts by ward into S3 as a single Parquet file.

Source: Nomis dataset NM_2077_1 (TS060 - Industry), Census 2021.
7,638 wards in England and Wales. One row per ward with counts of usual residents
aged 16+ in employment, broken down by SIC section (A–U, 18 industry groups).

Resident-based: counts where people *live*, not where they work.
Snapshot: Census 2021 only (no time series).

No partitioning — 7,638 rows, always scanned in full.
Join to other datasets via ward_cd (ONS ward code, e.g. 'E05012132').

Usage:
    python nomis_census_industry/nomis_census_industry_load.py
"""

import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3
from helpers.nomis import fetch_observations

S3_INCOMING_BUCKET = "dantelore.data.incoming"
S3_KEY = "nomis_census_industry/industry/industry_2021.parquet"
DATASET = "NM_2077_1"

# SIC section aggregate codes (1001–1018) plus total (0)
INDUSTRY_CODES = {
    0:    "total",
    1001: "agriculture_forestry_fishing",
    1002: "mining_quarrying",
    1003: "manufacturing",
    1004: "electricity_gas_steam",
    1005: "water_sewerage_waste",
    1006: "construction",
    1007: "wholesale_retail",
    1008: "transport_storage",
    1009: "accommodation_food",
    1010: "information_communication",
    1011: "financial_insurance",
    1012: "real_estate",
    1013: "professional_scientific",
    1014: "administrative_support",
    1015: "public_administration_defence",
    1016: "education",
    1017: "health_social_work",
    1018: "other",
}

COLUMNS = ["ward_cd", "ward_nm"] + list(INDUSTRY_CODES.values())


def fetch_category(code: int, col: str) -> pd.DataFrame:
    """Fetch one industry category for all wards, return ward_cd + col DataFrame."""
    obs = fetch_observations(DATASET, {
        "geography": "TYPE153",
        "c2021_ind_88": str(code),
        "measures": "20100",
        "date": "2021",
    })
    rows = [{"ward_cd": o["geography"]["geogcode"],
             "ward_nm": o["geography"]["description"],
             col: o["obs_value"]["value"]} for o in obs]
    df = pd.DataFrame(rows)
    df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df


def load():
    print("Fetching Census 2021 industry data (TS060) for all wards...")

    combined = None
    for code, col in INDUSTRY_CODES.items():
        print(f"  Fetching {col}...")
        df = fetch_category(code, col)
        if combined is None:
            combined = df
        else:
            combined = combined.merge(df[["ward_cd", col]], on="ward_cd", how="outer")

    df = combined[COLUMNS]
    for col in INDUSTRY_CODES.values():
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    print(f"  {len(df):,} wards")

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name

    df.to_parquet(tmp_path, index=False)
    load_file_to_s3(tmp_path, S3_INCOMING_BUCKET, S3_KEY)
    print("Done.")


if __name__ == "__main__":
    load()
