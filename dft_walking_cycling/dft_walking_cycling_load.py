"""
Load DfT walking and cycling statistics by local authority into S3: the share of adults who walk, cycle, or
walk or cycle, for any purpose, leisure or travel, at least once a month / week / 3 times a week / 5 times a
week, every year since 2016, for England, regions, counties and every local authority.

Source: gov.uk "Walking and cycling statistics (CW)", workbook CW0307 (all of tables CW0301 to CW0303,
unrounded, with confidence intervals and sample sizes), from Sport England's Active Lives Survey. The latest
edition replaces the previous one, so the table is overwritten on reload. Long format, one file, not partitioned.

Usage:
    python dft_walking_cycling/dft_walking_cycling_load.py
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
TABLE = "dft_walking_cycling_la"
PAGE = "https://www.gov.uk/api/content/government/statistical-data-sets/walking-and-cycling-statistics-cw"
WORKBOOK = "cw0307.ods"
KEYS = ["area_code", "area_name", "area_class", "mode", "purpose", "frequency"]


def workbook_url():
    page = requests.get(PAGE, timeout=60).json()
    url = next(a["url"] for a in page["details"]["attachments"] if a.get("url", "").endswith("/" + WORKBOOK))
    return url, page["public_updated_at"][:10]


def read_sheet(raw, value_name):
    """One of the CW0307 sheets, long format: KEYS, year, value_name."""
    header_row = raw.index[raw.iloc[:, 0].astype(str) == "ONS Code"][0]
    years = [int(float(y)) for y in raw.iloc[header_row, 6:]]
    df = raw.iloc[header_row + 1:].dropna(subset=[0]).copy()
    df.columns = KEYS + years
    df = df.melt(id_vars=KEYS, var_name="year", value_name=value_name)
    # Note markers (e.g. "[u]" suppressed, "[note 7]" no interval for restructured authorities) become null
    df[value_name] = pd.to_numeric(df[value_name], errors="coerce")
    return df


def load():
    url, published = workbook_url()
    sheets = pd.read_excel(io.BytesIO(requests.get(url, timeout=120).content), engine="odf", header=None,
                           sheet_name=["CW0307", "CW0307_ci", "CW0307_sample"])
    df = read_sheet(sheets["CW0307"], "pct")
    # The main sheet gets some authorities' class wrong (West Berkshire as a metropolitan district), so match the
    # sheets on code, mode, purpose and frequency, and take the class from the sample size sheet
    match = ["area_code", "mode", "purpose", "frequency", "year"]
    sample = read_sheet(sheets["CW0307_sample"], "sample_size")
    ci = read_sheet(sheets["CW0307_ci"], "ci_margin_pct")
    df = (df.drop(columns="area_class")
          .merge(sample[match + ["area_class", "sample_size"]], on=match, how="left", validate="one_to_one")
          .merge(ci[match + ["ci_margin_pct"]], on=match, how="left", validate="one_to_one"))
    # CW0307 writes suppressed proportions (fewer than 30 respondents) as 0
    df["is_suppressed"] = df["pct"].eq(0)
    df.loc[df["is_suppressed"], ["pct", "ci_margin_pct"]] = None
    df["year"] = df["year"].astype("int32")
    df["sample_size"] = df["sample_size"].astype("Int32")
    df["edition_published"] = published
    df = df[KEYS + ["year", "pct", "ci_margin_pct", "sample_size", "is_suppressed", "edition_published"]]
    with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
        df.to_parquet(tmp.name, index=False)
        load_file_to_s3(tmp.name, S3_INCOMING_BUCKET, f"{TABLE}/{TABLE}.parquet")
    print(f"  {len(df):,} rows, {df.area_code.nunique()} areas, {df.year.min()}-{df.year.max()}, "
          f"{df.is_suppressed.sum():,} suppressed")


if __name__ == "__main__":
    load()
