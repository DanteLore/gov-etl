"""
Load the Propensity to Cycle Tool (PCT, pct.bike) outputs into S3: how many people cycle to work (England and
Wales) and school (England) now, from the 2011 Census and 2011 School Census, and how many would under each
scenario, by area, by home-to-work pair, by school and on the route network.

- incoming.pct_commute_zones: per MSOA and LSOA of residence (geography_level partition)
- incoming.pct_commute_od: per home-work MSOA pair, all of England and Wales; per LSOA pair for the Berkshire
  region only (geography_level partition; the national LSOA file is 1.2 GB)
- incoming.pct_school_zones and incoming.pct_schools: per LSOA of residence, and per school
- incoming.pct_route_network: cyclists per road or path segment, as WKT lines, commute and school
  (purpose partition)

Columns are as published: <scenario>_<measure>, e.g. dutch_slc (cyclists under Go Dutch). See the catalogue entry.
Source: github.com/npct/pct-outputs-national and pct-outputs-regional-notR (Git LFS), last built in 2020.
Static: load once.

Usage:
    python pct/pct_load.py
    python pct/pct_load.py --part route_networks
"""

import argparse
import json
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
NATIONAL = "https://media.githubusercontent.com/media/npct/pct-outputs-national/master/"
REGIONAL = "https://media.githubusercontent.com/media/npct/pct-outputs-regional-notR/master/"
CODES = {c: str for c in ("geo_code", "geo_code1", "geo_code2", "lad11cd", "lad11cd1", "lad11cd2", "lsoa11cd", "urn", "id")}

# (table, partition column, partition value, source file)
CSV_FILES = [
    ("pct_commute_zones", "geography_level", "msoa", NATIONAL + "commute/msoa/z_all_attributes.csv"),
    ("pct_commute_zones", "geography_level", "lsoa", NATIONAL + "commute/lsoa/z_all_attributes.csv"),
    ("pct_commute_od", "geography_level", "msoa", NATIONAL + "commute/msoa/od_all_attributes.csv"),
    ("pct_commute_od", "geography_level", "lsoa", REGIONAL + "commute/lsoa/berkshire/od_attributes.csv"),
    ("pct_school_zones", None, None, NATIONAL + "school/lsoa/z_all_attributes.csv"),
]
RNET_FILES = [("commute", NATIONAL + "commute/lsoa/rnet_all.geojson"), ("school", NATIONAL + "school/lsoa/rnet_all.geojson")]
SCHOOLS = (NATIONAL + "school/lsoa/d_all_attributes.csv", NATIONAL + "school/lsoa/d_all.geojson")


def download(url, path):
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(16 << 20):
                f.write(chunk)
    return path


def snake(name):
    # The school files have a duplicated "dutch_sicarkm" column, read as "dutch_sicarkm.1"
    return re.sub(r"\W+", "_", name.strip()).lower()


def as_doubles(df):
    """Every number as a double: the same column is whole numbers in some files and decimals in others."""
    numbers = df.select_dtypes("number").columns
    df[numbers] = df[numbers].astype("float64")
    return df


def write(df, table, partition, value):
    key = f"{table}/{partition}={value}/{table}_{value}.parquet" if partition else f"{table}/{table}.parquet"
    with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
        df.to_parquet(tmp.name, index=False, compression="zstd")
        load_file_to_s3(tmp.name, S3_INCOMING_BUCKET, key)
    if partition:
        add_glue_partition(partition, value, table, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
    print(f"  {table} {value or ''}: {len(df):,} rows")


def load_csvs(tmp):
    for table, partition, value, url in CSV_FILES:
        df = pd.read_csv(download(url, Path(tmp) / "pct.csv"), dtype=CODES)
        df.columns = [snake(c) for c in df.columns]
        write(as_doubles(df), table, partition, value)


def load_route_networks(tmp):
    scenarios = ["bicycle", "govtarget_slc", "govnearmkt_slc", "gendereq_slc", "dutch_slc", "ebike_slc", "cambridge_slc"]
    for purpose, url in RNET_FILES:
        with open(download(url, Path(tmp) / "rnet.geojson")) as f:
            features = json.load(f)["features"]
        rows = []
        for feat in features:
            coords = feat["geometry"]["coordinates"]
            lons, lats = [c[0] for c in coords], [c[1] for c in coords]
            row = {"local_id": feat["properties"].get("local_id")}
            row.update({s: feat["properties"].get(s) for s in scenarios})
            row.update({"min_lon": min(lons), "min_lat": min(lats), "max_lon": max(lons), "max_lat": max(lats),
                        "geometry_wkt": "LINESTRING(" + ", ".join(f"{x} {y}" for x, y in coords) + ")"})
            rows.append(row)
        del features
        df = pd.DataFrame(rows)
        df["local_id"] = df["local_id"].astype("Int64")
        for s in scenarios:
            df[s] = df[s].astype("float64")
        write(df, "pct_route_network", "purpose", purpose)


def load_schools(tmp):
    attributes, points = SCHOOLS
    df = pd.read_csv(download(attributes, Path(tmp) / "d.csv"), dtype=CODES)
    df.columns = [snake(c) for c in df.columns]
    with open(download(points, Path(tmp) / "d.geojson")) as f:
        locations = {str(int(feat["properties"]["urn"])): feat["geometry"]["coordinates"] for feat in json.load(f)["features"]}
    df["longitude"] = df["urn"].map(lambda u: locations.get(u, [None, None])[0])
    df["latitude"] = df["urn"].map(lambda u: locations.get(u, [None, None])[1])
    write(as_doubles(df), "pct_schools", None, None)


PARTS = {"tables": load_csvs, "schools": load_schools, "route_networks": load_route_networks}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=list(PARTS))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        for part in [args.part] if args.part else PARTS:
            PARTS[part](tmp)
