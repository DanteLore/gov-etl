"""
Load VOA 2026 Compiled Rating List into S3, partitioned by postcode area.

Downloads the national baseline zip from the VOA open data portal. The file
is a single flat asterisk-delimited CSV with one record per hereditament
(non-domestic rated property). Partitioned by postcode area (e.g. 'rg', 'sw').

The file uses * as delimiter but the full_address field can itself contain *.
We handle this by anchoring on the fixed prefix (7 fields) and suffix (21 fields)
and treating everything in between as full_address.

Usage:
    python voa_rating_list/voa_rating_list_load.py
"""

import io
import re
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition_area

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"

DOWNLOAD_URL = (
    "https://voaratinglists.blob.core.windows.net/downloads/"
    "uk-englandwales-ndr-2026-listentries-compiled-epoch-0001-baseline-csv.zip"
)

CACHE_PATH = Path(tempfile.gettempdir()) / "voa_rating_list_download.zip"

INT64_MAX = 9_223_372_036_854_775_807

# Fields before and after full_address — used to anchor the line parser.
# full_address is at position 7 and may contain the * delimiter.
PREFIX_FIELDS = 7
SUFFIX_FIELDS = 21

COLUMNS = [
    "row_number",             # 0  — sequential, dropped after load
    "ba_code",                # 1
    "ndr_community_code",     # 2
    "uarn",                   # 3  — alphanumeric, not purely numeric
    "desc_code",              # 4
    "desc_text",              # 5
    "assessment_reference",   # 6
    "full_address",           # 7  — may contain *, handled by parse_line
    "_spare_8",               # 8
    "number_or_name",         # 9
    "street",                 # 10
    "town",                   # 11
    "postal_district",        # 12
    "county",                 # 13
    "postcode",               # 14
    "effective_date",         # 15
    "_spare_16",              # 16
    "rateable_value",         # 17
    "appeal_settlement_code", # 18
    "ba_reference",           # 19
    "list_alteration_date",   # 20
    "scat_code",              # 21
    "sub_street_1",           # 22
    "sub_street_2",           # 23
    "sub_street_3",           # 24
    "case_number",            # 25
    "current_from_date",      # 26
    "_spare_27",              # 27
    "_spare_28",              # 28
]

DROP_COLUMNS = ["row_number", "_spare_8", "_spare_16", "_spare_27", "_spare_28"]

DTYPES = {
    "ba_code":                str,
    "ndr_community_code":     str,
    "uarn":                   str,
    "desc_code":              str,
    "desc_text":              str,
    "assessment_reference":   "Int64",
    "full_address":           str,
    "number_or_name":         str,
    "street":                 str,
    "town":                   str,
    "postal_district":        str,
    "county":                 str,
    "postcode":               str,
    "effective_date":         str,
    "rateable_value":         "Int64",
    "appeal_settlement_code": str,
    "ba_reference":           str,
    "list_alteration_date":   str,
    "scat_code":              str,
    "sub_street_1":           str,
    "sub_street_2":           str,
    "sub_street_3":           str,
    "case_number":            "Int64",
    "current_from_date":      str,
}


def fetch_zip_bytes() -> bytes:
    if CACHE_PATH.exists():
        print(f"Using cached download: {CACHE_PATH}")
        return CACHE_PATH.read_bytes()
    print(f"Downloading {DOWNLOAD_URL}")
    response = requests.get(DOWNLOAD_URL, stream=True, timeout=600)
    response.raise_for_status()
    data = response.content
    CACHE_PATH.write_bytes(data)
    print(f"  Saved to {CACHE_PATH}")
    return data


def parse_line(line: str) -> list[str] | None:
    fields = line.rstrip("\r\n").split("*")
    if len(fields) < PREFIX_FIELDS + 1 + SUFFIX_FIELDS:
        return None
    full_address = "*".join(fields[PREFIX_FIELDS: len(fields) - SUFFIX_FIELDS])
    return fields[:PREFIX_FIELDS] + [full_address] + fields[len(fields) - SUFFIX_FIELDS:]


def to_int64(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.notna() & np.isfinite(numeric) & (numeric.abs() <= INT64_MAX)
    return pd.array(
        [int(v) if ok else pd.NA for v, ok in zip(numeric, valid)],
        dtype="Int64",
    )


def postcode_area(postcode: str) -> str:
    m = re.match(r"^([A-Za-z]+)", postcode.strip())
    return m.group(1).lower() if m else "unknown"


def parse(zip_bytes: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
        print(f"  Parsing {csv_name}...")
        with zf.open(csv_name) as f:
            rows, skipped = [], 0
            for raw in f:
                parsed = parse_line(raw.decode("latin-1"))
                if parsed is None:
                    skipped += 1
                else:
                    rows.append(parsed)

    if skipped:
        print(f"  Skipped {skipped:,} malformed lines")

    df = pd.DataFrame(rows, columns=COLUMNS)
    print(f"  {len(df):,} records")
    df = df.drop(columns=DROP_COLUMNS)

    for col, dtype in DTYPES.items():
        if dtype == "Int64":
            df[col] = to_int64(df[col])
        else:
            df[col] = df[col].astype(str).str.strip().replace({"nan": pd.NA, "": pd.NA})

    df["postcode_area"] = df["postcode"].fillna("").apply(postcode_area)
    return df


def load():
    zip_bytes = fetch_zip_bytes()
    df = parse(zip_bytes)

    areas = sorted(df["postcode_area"].unique())
    print(f"  {len(areas)} postcode areas")

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name

    for area in areas:
        area_df = df[df["postcode_area"] == area].drop(columns=["postcode_area"])
        area_df.to_parquet(tmp_path, index=False)

        s3_key = f"voa_rating_list/entries/postcode_area={area}/entries_{area}.parquet"
        load_file_to_s3(tmp_path, S3_INCOMING_BUCKET, s3_key)
        add_glue_partition_area(area, "voa_rating_list_entries", ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
        print(f"  Area {area}: {len(area_df):,} rows")

    print("Done.")


if __name__ == "__main__":
    load()
