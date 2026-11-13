"""
Load DfT's National Travel Survey (NTS) and National Travel Attitudes Study (NTAS) published tables into S3.

- incoming.dft_nts_tables: every NTS data table (NTS0101 to NTS9920 and the combined authority estimates), in one
  long format: table, sheet, year, up to three category columns (e.g. main mode, trip length), the measure
  (column heading) and its value. England, mostly 2002 onwards. Partitioned by table_id (e.g. nts0308).
- incoming.dft_ntas_responses: every question in NTAS waves 7 to 10 (2022 to 2024): question, who was asked,
  response, percentage and sample sizes, with breakdowns where published. Partitioned by wave.

Source: gov.uk NTS data table pages (one .ods per table) and the NTAS wave releases. Each NTS release revises
earlier years, so tables are replaced on reload. NTAS waves 1 to 6 use older one-off layouts and aren't loaded.
The survey microdata is only available from the UK Data Service under licence.

Usage:
    python dft_national_travel_survey/dft_national_travel_survey_load.py
    python dft_national_travel_survey/dft_national_travel_survey_load.py --table dft_ntas_responses
"""

import argparse
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
CONTENT_API = "https://www.gov.uk/api/content"
NTS_PAGES = [
    "nts01-average-number-of-trips-made-and-distance-travelled", "nts02-driving-licence-holders",
    "nts03-modal-comparisons", "nts04-purpose-of-trips", "nts05-trips", "nts06-age-gender-and-modal-breakdown",
    "nts07-car-ownership-and-access", "nts08-availability-and-distance-from-key-local-services",
    "nts09-vehicle-mileage-and-occupancy", "nts99-travel-by-region-and-area-type-of-residence",
    "national-travel-survey-combined-authority-estimates",
]
NTAS_WAVES = {7: "national-travel-attitudes-study-wave-7", 8: "national-travel-attitudes-study-wave-8",
              9: "national-travel-attitudes-study-wave-9", 10: "national-travel-attitudes-study-wave-10"}
MAX_DIMENSIONS = 3
NTS_COLUMNS = (["sheet", "sheet_title", "year_label", "year"]
               + [c for i in range(1, MAX_DIMENSIONS + 1) for c in (f"dimension_{i}_name", f"dimension_{i}")]
               + ["measure", "value", "value_marker", "sample_size", "sample_size_label", "edition_published"])
NTAS_COLUMNS = ["sheet", "sheet_title", "question", "question_base", "response", "comparison_variable",
                "comparison_value", "pct", "value_marker", "sample_size_response", "sample_size_base", "notes",
                "variable_name", "edition_published"]


def clean(cell):
    """Strip note markers ("[note 3]", "[notes 2, 3]") and extra spaces from a label."""
    if not isinstance(cell, str):
        return cell
    return re.sub(r"\s+", " ", re.sub(r"\s*\[notes? [^\]]*\]", "", cell, flags=re.I)).strip()


def page(path):
    return requests.get(f"{CONTENT_API}/government/{path}", timeout=60).json()


def ods_attachments(path):
    p = page(path)
    for a in p["details"].get("attachments", []):
        if a.get("url", "").endswith(".ods"):
            yield a["url"], p["public_updated_at"][:10]


def read_workbook(url):
    return pd.read_excel(io.BytesIO(requests.get(url, timeout=300).content), sheet_name=None, engine="odf", header=None)


def write(df, table, partition, value):
    with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
        df.to_parquet(tmp.name, index=False, compression="zstd")
        load_file_to_s3(tmp.name, S3_INCOMING_BUCKET, f"{table}/{partition}={value}/{table}_{value}.parquet")
    add_glue_partition(partition, str(value), table, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)


def _number(cell):
    if isinstance(cell, str):
        return None
    return None if pd.isna(cell) else float(cell)


def nts_sheet(sheet, raw, published):
    """One NTS data sheet in long format, or None if it doesn't have the usual Year-first layout."""
    if raw.empty:
        return None
    first = raw.iloc[:, 0].map(clean).astype(str)
    header_rows = raw.index[first.str.match(r"^Year\b")]
    if not len(header_rows):
        return None
    h = header_rows[0]
    header = [clean(str(c)) for c in raw.iloc[h]]
    rows = raw.iloc[h + 1:].dropna(subset=[0])
    rows = rows[rows.iloc[:, 0].astype(str).str.match(r"^\d{4}")]
    if rows.empty:
        return None
    sample_cols = [i for i, c in enumerate(header) if c.lower().startswith("unweighted sample")]
    # Category columns are the text columns after Year, up to the first numeric one
    dims = []
    for i in range(1, len(header)):
        if i in sample_cols or pd.to_numeric(rows.iloc[:, i], errors="coerce").notna().any():
            break
        dims.append(i)
    if len(dims) > MAX_DIMENSIONS:
        raise ValueError(f"{sheet}: {len(dims)} category columns")
    measures = [i for i in range(1 + len(dims), len(header)) if i not in sample_cols and header[i] != "nan"]
    out = []
    for _, r in rows.iterrows():
        base = {"sheet": sheet, "sheet_title": clean(raw.iloc[0, 0]), "year_label": str(r.iloc[0]).split(".")[0],
                "edition_published": published}
        base["year"] = int(base["year_label"][:4])
        for n, i in enumerate(dims, 1):
            base[f"dimension_{n}_name"], base[f"dimension_{n}"] = header[i], clean(r.iloc[i])
        if sample_cols:
            base["sample_size"], base["sample_size_label"] = _number(r.iloc[sample_cols[0]]), header[sample_cols[0]]
        for i in measures:
            cell = r.iloc[i]
            out.append({**base, "measure": header[i], "value": _number(cell),
                        "value_marker": cell if isinstance(cell, str) else None})
    return pd.DataFrame(out, columns=NTS_COLUMNS)


def load_nts():
    table = "dft_nts_tables"
    seen, skipped = set(), []
    for path in NTS_PAGES:
        for url, published in ods_attachments(f"statistical-data-sets/{path}"):
            table_id = url.rsplit("/", 1)[-1].removesuffix(".ods").lower()
            if table_id in seen:
                continue
            seen.add(table_id)
            frames = []
            for sheet, raw in read_workbook(url).items():
                # Sheet names starting with a quote are external links left in some workbooks, not sheets
                if sheet.startswith("'") or sheet.lower().startswith(("cover", "table_of_contents", "contents", "notes")):
                    continue
                df = nts_sheet(sheet, raw, published)
                if df is None:
                    skipped.append(f"{table_id}/{sheet}")
                else:
                    frames.append(df)
            if not frames:
                continue
            df = pd.concat(frames, ignore_index=True)
            df["year"] = df["year"].astype("int32")
            text = [c for c in NTS_COLUMNS if c not in ("year", "value", "sample_size")]
            df[text] = df[text].astype("string")
            write(df, table, "table_id", table_id)
            print(f"  {table_id}: {len(frames)} sheets, {len(df):,} rows")
    if skipped:
        print(f"  Sheets without the usual layout, not loaded: {', '.join(skipped)}")


def ntas_sheet(sheet, raw, title, published):
    """One NTAS question table, or None if it isn't one."""
    first = raw.iloc[:, 0].astype(str)
    header_rows = raw.index[first == "Question"]
    if not len(header_rows):
        return None
    h = header_rows[0]
    header = [str(c).strip().rstrip(":") for c in raw.iloc[h]]
    rows = raw.iloc[h + 1:].dropna(subset=[0])

    def col(*names):
        for name in names:
            for i, c in enumerate(header):
                if c.lower().startswith(name.lower()):
                    return rows.iloc[:, i]
        return pd.Series([None] * len(rows), index=rows.index)

    pct = col("Percentage")
    df = pd.DataFrame({
        "sheet": sheet, "sheet_title": title, "question": col("Question").map(clean),
        "question_base": col("Question asked of", "Question base"), "response": col("Response"),
        "comparison_variable": col("Comparison variable"), "comparison_value": col("Comparison value"),
        "pct": pd.to_numeric(pct, errors="coerce"),
        "value_marker": pct.where(pct.map(lambda v: isinstance(v, str))),
        "sample_size_response": pd.to_numeric(col("Unweighted sample size (Response)"), errors="coerce"),
        "sample_size_base": pd.to_numeric(col("Unweighted sample size (Question asked of)", "Unweighted sample size"),
                                          errors="coerce"),
        "notes": col("Notes"), "variable_name": col("Variable Name"), "edition_published": published,
    })
    for c in ("sample_size_response", "sample_size_base"):
        df[c] = df[c].astype("Int32")
    for c in ("question_base", "response", "comparison_variable", "comparison_value", "value_marker", "notes",
              "variable_name"):
        df[c] = df[c].astype("string")
    return df[NTAS_COLUMNS]


def load_ntas():
    table = "dft_ntas_responses"
    for wave, path in NTAS_WAVES.items():
        url, published = next(ods_attachments(f"statistics/{path}"))
        sheets = read_workbook(url)
        contents = sheets.get("Table_of_contents")
        titles = dict(zip(contents[0].astype(str), contents[1])) if contents is not None else {}
        frames = []
        for sheet, raw in sheets.items():
            # All-question sheets repeat the topic sheets; Question_explorer is an interactive view
            if not re.match(r"(?i)^NTAS_\d+[a-z]$", sheet) or re.search(r"(?i)all questions", str(titles.get(sheet))):
                continue
            df = ntas_sheet(sheet, raw, titles.get(sheet, clean(raw.iloc[0, 0])), published)
            if df is not None:
                frames.append(df)
        df = pd.concat(frames, ignore_index=True)
        write(df, table, "wave", wave)
        print(f"  wave {wave}: {len(frames)} sheets, {df.question.nunique()} questions, {len(df):,} rows")


TABLES = {"dft_nts_tables": load_nts, "dft_ntas_responses": load_ntas}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", choices=list(TABLES))
    args = parser.parse_args()
    for t in [args.table] if args.table else TABLES:
        print(f"Loading {t}...")
        TABLES[t]()
