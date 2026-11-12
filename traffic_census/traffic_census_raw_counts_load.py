"""
Load DfT raw traffic counts into S3: the hour-by-hour manual counts behind the AADF figures.

Source: dft_traffic_counts_raw_counts.zip (about 5 million rows, one CSV). One row per count point, direction,
count date and hour (07:00 to 18:00), with vehicles counted by type. Partitioned by year, like
incoming.traffic_census_aadf, and joins to it on count_point_id, year and direction_of_travel.

Usage:
    python traffic_census/traffic_census_raw_counts_load.py
"""

import io
import sys
import tempfile
import zipfile
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pv
import pyarrow.parquet as pq
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition_y

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"
TABLE = "traffic_census_raw_counts"
URL = "https://storage.googleapis.com/dft-statistics/road-traffic/downloads/data-gov-uk/dft_traffic_counts_raw_counts.zip"

STRINGS = ["direction_of_travel", "region_name", "region_ons_code", "local_authority_name", "local_authority_code",
           "road_name", "road_category", "road_type", "start_junction_road_name", "end_junction_road_name"]
DOUBLES = ["latitude", "longitude", "link_length_km", "link_length_miles"]
INTS = ["count_point_id", "year", "hour", "region_id", "local_authority_id", "easting", "northing",
        "pedal_cycles", "two_wheeled_motor_vehicles", "cars_and_taxis", "buses_and_coaches", "lgvs",
        "hgvs_2_rigid_axle", "hgvs_3_rigid_axle", "hgvs_4_or_more_rigid_axle", "hgvs_3_or_4_articulated_axle",
        "hgvs_5_articulated_axle", "hgvs_6_articulated_axle", "all_hgvs", "all_motor_vehicles"]


def load():
    print(f"Downloading {URL}...")
    r = requests.get(URL, timeout=600)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf, zf.open(zf.namelist()[0]) as f:
        header = f.readline().decode().strip().replace('"', "").split(",")
    names = [c.lower() for c in header]
    types = {n: pa.string() for n in STRINGS} | {n: pa.float64() for n in DOUBLES} | {n: pa.int32() for n in INTS}
    types["count_date"] = pa.date32()
    if set(names) != set(types):
        raise ValueError(f"Unexpected columns: {sorted(set(names) ^ set(types))}")
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf, zf.open(zf.namelist()[0]) as f:
        table = pv.read_csv(f, read_options=pv.ReadOptions(column_names=names, skip_rows=1),
                            convert_options=pv.ConvertOptions(column_types=types))
    print(f"{table.num_rows:,} rows")
    for year in sorted(pc.unique(table["year"]).to_pylist()):
        part = table.filter(pc.equal(table["year"], year)).drop_columns(["year"])
        with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
            pq.write_table(part, tmp.name, compression="snappy")
            load_file_to_s3(tmp.name, S3_INCOMING_BUCKET, f"traffic_census/raw_counts/year={year}/raw_counts_{year}.parquet")
        add_glue_partition_y(year, TABLE, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
        print(f"  {year}: {part.num_rows:,} rows")


if __name__ == "__main__":
    load()
