"""
Load ONS Small Area Income Estimates (MSOA level) into S3 as Parquet.

Downloads the latest published Excel workbook (financial year ending 2023) from ONS.
Four income types are extracted and joined into one wide table, one row per MSOA:

  total_annual_income          — total gross household income
  net_annual_income            — disposable (net) household income
  net_income_before_housing    — equivalised net income before housing costs
  net_income_after_housing     — equivalised net income after housing costs

Each measure also has upper/lower confidence limits and confidence interval columns.

Source: ONS Small Area Income Estimates for MSOAs, England and Wales.
No partitioning — 7,264 rows, always scanned in full.

Usage:
    python ons_msoa_income/ons_msoa_income_load.py
"""

import io
import sys
import tempfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3

S3_INCOMING_BUCKET = "dantelore.data.incoming"
S3_KEY = "ons_msoa_income/income/msoa_income_2023.parquet"

DOWNLOAD_URL = (
    "https://www.ons.gov.uk/file?uri=/employmentandlabourmarket/peopleinwork"
    "/earningsandworkinghours/datasets/smallareaincomeestimatesformiddlelayer"
    "superoutputareasenglandandwales/financialyearending2023/datasetfinal.xlsx"
)

# (sheet_name, value_column_prefix)
SHEETS = [
    ("Total annual income",           "total_annual_income"),
    ("Net annual income",              "net_annual_income"),
    ("Net income before housing costs","net_income_before_housing"),
    ("Net income after housing costs", "net_income_after_housing"),
]


def read_sheet(xl: pd.ExcelFile, sheet_name: str, prefix: str) -> pd.DataFrame:
    # Data rows start at row index 2 (0-based), first row is header
    df = pd.read_excel(xl, sheet_name=sheet_name, header=2)
    df.columns = [str(c).strip() for c in df.columns]

    # First column is MSOA code, second is MSOA name — rest follow a fixed pattern
    code_col = df.columns[0]
    name_col = df.columns[1]
    lad_code_col = df.columns[2]
    lad_name_col = df.columns[3]
    rgn_code_col = df.columns[4]
    rgn_name_col = df.columns[5]
    value_col = df.columns[6]
    upper_col = df.columns[7]
    lower_col = df.columns[8]
    ci_col = df.columns[9]

    out = df[[code_col, name_col, lad_code_col, lad_name_col, rgn_code_col, rgn_name_col,
              value_col, upper_col, lower_col, ci_col]].copy()
    out.columns = [
        "msoa21cd", "msoa21nm", "lad_code", "lad_name", "rgn_code", "rgn_name",
        prefix,
        f"{prefix}_upper_ci",
        f"{prefix}_lower_ci",
        f"{prefix}_ci",
    ]

    # Drop header/footer rows — keep only rows where msoa21cd looks like an MSOA code
    out = out[out["msoa21cd"].str.match(r"^[EW]\d+$", na=False)].copy()

    for col in [prefix, f"{prefix}_upper_ci", f"{prefix}_lower_ci", f"{prefix}_ci"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").astype("float64")

    return out


def load():
    print("Downloading ONS MSOA income workbook...")
    r = requests.get(DOWNLOAD_URL, timeout=120)
    r.raise_for_status()
    print(f"  {len(r.content) / 1024 / 1024:.1f} MB downloaded")

    xl = pd.ExcelFile(io.BytesIO(r.content))

    dfs = []
    for sheet_name, prefix in SHEETS:
        print(f"  Reading sheet: {sheet_name}...")
        df = read_sheet(xl, sheet_name, prefix)
        print(f"    {len(df)} rows")
        dfs.append(df)

    # Join all income types on MSOA code — use first sheet for the shared columns
    combined = dfs[0]
    for df in dfs[1:]:
        value_cols = [c for c in df.columns if c not in ("msoa21cd", "msoa21nm", "lad_code", "lad_name", "rgn_code", "rgn_name")]
        combined = combined.merge(df[["msoa21cd"] + value_cols], on="msoa21cd", how="outer")

    combined = combined.sort_values("msoa21cd").reset_index(drop=True)
    print(f"  {len(combined)} MSOAs in combined table")

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name

    combined.to_parquet(tmp_path, index=False)
    load_file_to_s3(tmp_path, S3_INCOMING_BUCKET, S3_KEY)
    print("Done.")


if __name__ == "__main__":
    load()
