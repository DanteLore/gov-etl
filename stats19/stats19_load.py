"""
Load DfT road safety data (STATS19) into S3: every reported injury collision in Great Britain since 1979,
with its vehicles and casualties.

Source: data.dft.gov.uk/road-accidents-safety-data/, the three "1979-latest-published-year" CSVs
(about 1.5 GB each). Column names and codes are kept as published: codes and counts as int, coordinates
and severity adjustments as double, `date` as a date, identifiers and LSOA codes as string.
Decode the codes with the DfT data guide (dft-road-casualty-statistics-road-safety-open-dataset-data-guide).

Tables, all partitioned by collision_year so the annual release only replaces whole years:
    incoming.stats19_collisions   one row per collision, with location (OSGB36 and lat/lon)
    incoming.stats19_vehicles     one row per vehicle, joins on collision_index
    incoming.stats19_casualties   one row per casualty, joins on collision_index and vehicle_reference

Usage:
    python stats19/stats19_load.py
    python stats19/stats19_load.py --table collision
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pv
import pyarrow.dataset as ds
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"
URL = "https://data.dft.gov.uk/road-accidents-safety-data/dft-road-casualty-statistics-{table}-1979-latest-published-year.csv"

TABLES = {"collision": "stats19_collisions", "vehicle": "stats19_vehicles", "casualty": "stats19_casualties"}

# Every other column is a whole-number code or count (int); a new column that isn't fails the int cast
STRINGS = {"collision_index", "collision_year", "collision_ref_no", "time", "local_authority_ons_district",
           "local_authority_highway", "local_authority_highway_current", "lsoa_of_accident_location",
           "generic_make_model", "lsoa_of_driver", "lsoa_of_casualty"}
DOUBLES = {"longitude", "latitude", "collision_adjusted_severity_serious", "collision_adjusted_severity_slight",
           "casualty_adjusted_severity_serious", "casualty_adjusted_severity_slight"}


def column_type(name):
    return (pa.date32() if name == "date" else pa.string() if name in STRINGS
            else pa.float64() if name in DOUBLES else pa.int32())


def converted(path, schema):
    """The CSV's batches with each column converted to its type (collision_year stays a string: the partition)."""
    names = schema.names
    reader = pv.open_csv(path, read_options=pv.ReadOptions(block_size=64 << 20),
                         convert_options=pv.ConvertOptions(column_types={n: pa.string() for n in names},
                                                           strings_can_be_null=True))
    for batch in reader:
        arrays = []
        for field, column in zip(schema, batch.columns):
            if field.name == "date":
                column = pc.cast(pc.strptime(column, "%d/%m/%Y", "s"), pa.date32())
            elif field.type != pa.string():
                column = pc.cast(column, field.type)
            arrays.append(column)
        yield pa.RecordBatch.from_arrays(arrays, schema=schema)


def load(source):
    table = TABLES[source]
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / f"{source}.csv"
        print(f"Downloading {URL.format(table=source)}...")
        with requests.get(URL.format(table=source), stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(csv_path, "wb") as f:
                shutil.copyfileobj(r.raw, f, length=16 << 20)

        schema = pa.schema([(n, column_type(n)) for n in pv.open_csv(csv_path).schema.names])
        out = Path(tmp) / table
        ds.write_dataset(converted(csv_path, schema), out, schema=schema, format="parquet",
                         partitioning=ds.partitioning(pa.schema([("collision_year", pa.string())]), flavor="hive"),
                         basename_template=f"{table}_{{i}}.parquet", max_rows_per_group=1 << 20,
                         existing_data_behavior="overwrite_or_ignore")
        for year_dir in sorted(out.iterdir()):
            year = year_dir.name.split("=", 1)[1]
            (part,) = year_dir.iterdir()
            load_file_to_s3(str(part), S3_INCOMING_BUCKET, f"stats19/{table}/collision_year={year}/{table}_{year}.parquet")
            add_glue_partition("collision_year", year, table, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
        print(f"{table}: {len(list(out.iterdir()))} years, columns: " + ", ".join(f"{f.name} {f.type}" for f in schema))
    return schema


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", choices=list(TABLES))
    args = parser.parse_args()
    for t in [args.table] if args.table else TABLES:
        load(t)
