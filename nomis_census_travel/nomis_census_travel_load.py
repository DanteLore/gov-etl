"""
Load three Census 2021 travel topic summaries into S3, at output area, LSOA, MSOA, local authority and ward level:

- TS061 method used to travel to work  -> incoming.nomis_census_travel_method
- TS058 distance travelled to work     -> incoming.nomis_census_travel_distance
- TS045 car or van availability         -> incoming.nomis_census_car_availability

Source: the Nomis bulk downloads (output areas to local authorities) and the Nomis API (2022 wards).
All of England and Wales. One row per area, one column per category, partitioned by geography_level
(oa, lsoa, msoa, ltla, ward). Census 2021 snapshot: load once.

Usage:
    python nomis_census_travel/nomis_census_travel_load.py
    python nomis_census_travel/nomis_census_travel_load.py --table nomis_census_car_availability
"""

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition
from helpers.nomis import census_topic_levels

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"

# table -> (topic, Nomis dataset, category dimension, columns in the source's category order)
TOPICS = {
    "nomis_census_travel_method": ("ts061", "NM_2078_1", "c2021_ttwmeth_12", [
        "total", "work_from_home", "underground_metro_tram", "train", "bus_coach", "taxi", "motorcycle",
        "car_driver", "car_passenger", "bicycle", "on_foot", "other"]),
    "nomis_census_travel_distance": ("ts058", "NM_2075_1", "c2021_ttwdist_11", [
        "total", "under_2km", "from_2_to_5km", "from_5_to_10km", "from_10_to_20km", "from_20_to_30km",
        "from_30_to_40km", "from_40_to_60km", "km_60_and_over", "work_from_home", "offshore_no_fixed_place_or_abroad"]),
    "nomis_census_car_availability": ("ts045", "NM_2063_1", "c2021_cars_5", [
        "total_households", "no_car", "one_car", "two_cars", "three_or_more_cars"]),
}


def load(table):
    topic, dataset, dimension, columns = TOPICS[table]
    print(f"Loading {table} ({topic.upper()})...")
    for level, df in census_topic_levels(topic, dataset, dimension, columns):
        with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
            df.to_parquet(tmp.name, index=False)
            load_file_to_s3(tmp.name, S3_INCOMING_BUCKET, f"{table}/geography_level={level}/{table}_{level}.parquet")
        add_glue_partition("geography_level", level, table, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
        print(f"  {level}: {len(df):,} areas")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", choices=list(TOPICS))
    args = parser.parse_args()
    for t in [args.table] if args.table else TOPICS:
        load(t)
