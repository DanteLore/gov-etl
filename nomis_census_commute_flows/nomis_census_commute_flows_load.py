"""
Load Census 2021 origin-destination flows from home to workplace (ODWP01EW) into S3.

Source: Nomis bulk download odwp01ew.zip. All of England and Wales. One row per home area, workplace area
and place-of-work category, with the count of usual residents aged 16+. Loaded at output area, MSOA and
local authority level, partitioned by geography_level (oa, msoa, ltla).
Census 2021 snapshot: load once.

Usage:
    python nomis_census_commute_flows/nomis_census_commute_flows_load.py
"""

import io
import sys
import tempfile
import zipfile
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pv
import pyarrow.parquet as pq
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"
TABLE = "nomis_census_commute_flows"
URL = "https://www.nomisweb.co.uk/output/census/2021/odwp01ew.zip"

LEVELS = {"oa": "ODWP01EW_OA.csv", "msoa": "ODWP01EW_MSOA.csv", "ltla": "ODWP01EW_LTLA.csv"}
COLUMNS = ["home_code", "home_name", "workplace_code", "workplace_name", "place_of_work_code", "place_of_work_name", "count"]
TYPES = {c: pa.string() for c in COLUMNS} | {"place_of_work_code": pa.int32(), "count": pa.int32()}


def load():
    print(f"Downloading {URL}...")
    r = requests.get(URL, timeout=600)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        for level, name in LEVELS.items():
            with zf.open(name) as f:
                table = pv.read_csv(f, read_options=pv.ReadOptions(column_names=COLUMNS, skip_rows=1),
                                    convert_options=pv.ConvertOptions(column_types=TYPES))
            with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
                pq.write_table(table, tmp.name, compression="snappy")
                load_file_to_s3(tmp.name, S3_INCOMING_BUCKET, f"{TABLE}/geography_level={level}/{TABLE}_{level}.parquet")
            add_glue_partition("geography_level", level, TABLE, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
            print(f"  {level}: {table.num_rows:,} flows")


if __name__ == "__main__":
    load()
