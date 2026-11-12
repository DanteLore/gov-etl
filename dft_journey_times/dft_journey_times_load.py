"""
Load DfT journey time statistics by LSOA (tables JTS0501 to JTS0509) into S3: modelled minimum travel times
from each LSOA in England to employment centres, schools, further education, GPs, hospitals, food stores,
town centres and pharmacies, by public transport/walk, cycle, car and walking.

Source: gov.uk "Journey time statistics: data tables (JTS)". Each table's latest year sheet is loaded
(2019, published November 2021, is the latest edition). Long format: one row per LSOA, table and field, with
the field's description from the table's metadata sheet. Partitioned by edition_year.

Usage:
    python dft_journey_times/dft_journey_times_load.py
"""

import io
import re
import sys
import tempfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"
TABLE = "dft_journey_times_lsoa"
PAGE = "https://www.gov.uk/api/content/government/statistical-data-sets/journey-time-statistics-data-tables-jts"
REFERENCE = {"LSOA_code": "lsoa_code", "Region": "region", "LA_Code": "la_code", "LA_Name": "la_name"}
MODES = [("by PT/walk", "public transport or walk"), ("by cycle", "cycle"), ("by car", "car"), ("by walk", "walk")]


def lsoa_tables():
    """(table id, title, url) for each LSOA-level JTS table on the gov.uk page."""
    attachments = requests.get(PAGE, timeout=60).json()["details"]["attachments"]
    for a in attachments:
        match = re.search(r"(jts05\d\d)\.ods$", a.get("url", ""))
        if match:
            yield match.group(1), a["title"].strip(), a["url"]


def read_table(table_id, title, url):
    sheets = pd.read_excel(io.BytesIO(requests.get(url, timeout=300).content), sheet_name=None, engine="calamine", header=None)
    year = max(name for name in sheets if re.fullmatch(r"\d{4}", name))
    meta = sheets["Metadata"]
    header_row = meta.index[meta.iloc[:, 1].astype(str).eq("Field")][0]
    descriptions = {str(r[1]).strip(): str(r[3]).strip() for r in meta.iloc[header_row + 1:].itertuples(index=False)
                    if pd.notna(r[1]) and pd.notna(r[3])}

    data = sheets[year]
    names_row = data.index[data.iloc[:, 0].astype(str).str.lower().eq("lsoa_code")][0]
    data = data.iloc[names_row + 1:].copy()
    data.columns = [str(c).strip() for c in sheets[year].iloc[names_row]]
    data = data.rename(columns={c: REFERENCE[k] for c in data.columns for k in REFERENCE if c.lower() == k.lower()})
    data = data.dropna(subset=["lsoa_code"])
    long = data.melt(id_vars=list(REFERENCE.values()), var_name="field", value_name="value")
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    long["field_description"] = long["field"].map(lambda f: descriptions.get(f, descriptions.get(f.replace("_", ""))))
    long["mode"] = long["field_description"].map(
        lambda d: next((mode for phrase, mode in MODES if d and phrase in d), None))
    long.insert(4, "table_id", table_id)
    long.insert(5, "table_title", title)
    return year, long[list(REFERENCE.values()) + ["table_id", "table_title", "field", "field_description", "mode", "value"]]


def load():
    for table_id, title, url in lsoa_tables():
        year, df = read_table(table_id, title, url)
        missing = df.loc[df["field_description"].isna(), "field"].unique()
        if len(missing):
            raise ValueError(f"{table_id}: no metadata for fields {list(missing)}")
        with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
            df.to_parquet(tmp.name, index=False)
            load_file_to_s3(tmp.name, S3_INCOMING_BUCKET, f"{TABLE}/edition_year={year}/{TABLE}_{table_id}.parquet")
        add_glue_partition("edition_year", year, TABLE, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
        print(f"  {table_id} ({year}): {df['lsoa_code'].nunique():,} LSOAs, {df['field'].nunique()} fields - {title}")


if __name__ == "__main__":
    load()
