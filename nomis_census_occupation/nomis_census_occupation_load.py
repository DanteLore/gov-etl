"""
Load Census 2021 occupation (TS063) counts by ward into S3 as a single Parquet file.

Source: Nomis dataset NM_2080_1 (TS063 - Occupation), Census 2021.
7,638 wards in England and Wales. One row per ward with counts of usual residents
aged 16+ in employment, broken down by SOC major group (9 groups plus total).

Resident-based: counts where people *live*, not where they work.
Snapshot: Census 2021 only (no time series).

No partitioning — 7,638 rows, always scanned in full.
Join to other datasets via ward_cd (ONS ward code, e.g. 'E05012132').

Usage:
    python nomis_census_occupation/nomis_census_occupation_load.py
"""

import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3
from helpers.nomis import fetch_observations

S3_INCOMING_BUCKET = "dantelore.data.incoming"
S3_KEY = "nomis_census_occupation/occupation/occupation_2021.parquet"
DATASET = "NM_2080_1"

# SOC 2020 major group codes (0 = total, 1–9 = major groups)
OCCUPATION_CODES = {
    0: "total",
    1: "managers_directors_senior_officials",
    2: "professional",
    3: "associate_professional_technical",
    4: "administrative_secretarial",
    5: "skilled_trades",
    6: "caring_leisure_service",
    7: "sales_customer_service",
    8: "process_plant_machine_operatives",
    9: "elementary",
}

COLUMNS = ["ward_cd", "ward_nm"] + list(OCCUPATION_CODES.values())


def fetch_category(code: int, col: str) -> pd.DataFrame:
    """Fetch one occupation category for all wards, return ward_cd + col DataFrame."""
    obs = fetch_observations(DATASET, {
        "geography": "TYPE153",
        "c2021_occ_10": str(code),
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
    print("Fetching Census 2021 occupation data (TS063) for all wards...")

    combined = None
    for code, col in OCCUPATION_CODES.items():
        print(f"  Fetching {col}...")
        df = fetch_category(code, col)
        if combined is None:
            combined = df
        else:
            combined = combined.merge(df[["ward_cd", col]], on="ward_cd", how="outer")

    df = combined[COLUMNS]
    for col in OCCUPATION_CODES.values():
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    print(f"  {len(df):,} wards")

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name

    df.to_parquet(tmp_path, index=False)
    load_file_to_s3(tmp_path, S3_INCOMING_BUCKET, S3_KEY)
    print("Done.")


if __name__ == "__main__":
    load()
