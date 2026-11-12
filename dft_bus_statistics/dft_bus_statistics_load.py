"""
Load DfT local bus statistics by local authority into S3: passenger journeys (BUS01e-h), vehicle miles by
service type (BUS02d) and punctuality (BUS09a-b), England, annual by financial year.

Source: gov.uk "Bus statistics data tables". The current edition replaces the previous one (DfT revises
earlier years), so the table is overwritten on reload. Long format: one row per table, area (local authority,
or region and England totals as published), service type where given, and year ending March.
Partitioned by table_id.

Usage:
    python dft_bus_statistics/dft_bus_statistics_load.py
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
TABLE = "dft_bus_statistics_la"
PAGE = "https://www.gov.uk/api/content/government/statistical-data-sets/bus-statistics-data-tables"

# workbook -> local authority sheets to load
WORKBOOKS = {
    "bus01.ods": ["BUS01e", "BUS01f", "BUS01g", "BUS01h"],
    "bus02_mi.ods": ["BUS02d_mi"],
    "bus09.ods": ["BUS09a", "BUS09b"],
}
COLUMNS = ["table_id", "table_title", "unit", "area_code", "area_name", "region", "service_type",
           "year_ending_march", "year_label", "value", "value_marker", "notes", "edition_published"]


def workbook_urls():
    for a in requests.get(PAGE, timeout=60).json()["details"]["attachments"]:
        name = a.get("url", "").rsplit("/", 1)[-1]
        if name in WORKBOOKS:
            yield name, a["url"]


def _clean(cell):
    return re.sub(r"\s+", " ", cell).strip() if isinstance(cell, str) else cell


def read_sheet(sheet, raw, published):
    raw = raw.map(_clean)
    header_row = raw.index[raw.iloc[:, 0].astype(str).str.match(r"(?i)^(la code|local authority)")][0]
    header = [str(h) for h in raw.iloc[header_row]]
    unit = raw.iloc[header_row - 1, 0]
    rows = raw.iloc[header_row + 1:].dropna(subset=[0])

    year_cols = [i for i, h in enumerate(header) if re.match(r"^\d{4}", h)]
    named = {h.lower(): i for i, h in enumerate(header)}
    name_col = next(i for i, h in enumerate(header) if i and h.lower() in ("la", "la or region", "local authority"))
    region_col = named.get("region")
    service_col = named.get("service type")
    notes_col = named.get("notes")

    out = []
    for _, r in rows.iterrows():
        for i in year_cols:
            cell = r.iloc[i]
            number = pd.to_numeric(cell, errors="coerce") if not isinstance(cell, str) else None
            out.append({
                "table_id": sheet, "table_title": raw.iloc[0, 0], "unit": unit,
                "area_code": r.iloc[0], "area_name": r.iloc[name_col],
                "region": r.iloc[region_col] if region_col is not None else None,
                "service_type": r.iloc[service_col] if service_col is not None else None,
                "year_ending_march": int(header[i][:4]), "year_label": header[i],
                "value": None if number is None or pd.isna(number) else float(number),
                "value_marker": cell if isinstance(cell, str) else None,
                "notes": r.iloc[notes_col] if notes_col is not None else None,
                "edition_published": published,
            })
    return pd.DataFrame(out, columns=COLUMNS)


def load():
    published = requests.get(PAGE, timeout=60).json()["public_updated_at"][:10]
    for name, url in workbook_urls():
        sheets = pd.read_excel(io.BytesIO(requests.get(url, timeout=120).content), sheet_name=WORKBOOKS[name],
                               engine="odf", header=None)
        for sheet, raw in sheets.items():
            df = read_sheet(sheet, raw, published)
            with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
                df.to_parquet(tmp.name, index=False)
                load_file_to_s3(tmp.name, S3_INCOMING_BUCKET, f"{TABLE}/table_id={sheet.lower()}/{TABLE}_{sheet.lower()}.parquet")
            add_glue_partition("table_id", sheet.lower(), TABLE, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
            print(f"  {sheet}: {df['area_code'].nunique()} areas, {df['year_ending_march'].min()}-{df['year_ending_march'].max()} - {df['table_title'].iloc[0][:90]}")


if __name__ == "__main__":
    load()
