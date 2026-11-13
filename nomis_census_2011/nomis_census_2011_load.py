"""
Load Census 2011 travel to work data into S3, for comparison with Census 2021 (and because many local plans'
trip rates are still built on 2011 travel patterns):

- QS701EW method of travel to work, by output area, LSOA, MSOA, ward and local authority
  -> incoming.nomis_census_2011_travel_method
- WU03EW home-to-workplace flows by method of travel, MSOA and local authority
  -> incoming.nomis_census_2011_commute_flows

Source: Nomis whole-table downloads (`.bulk.csv` on the API), except the MSOA flows, which come from the ONS
file of non-zero flows archived by Jisc. Output area flows (WF01BEW) aren't loaded: Nomis only offers them as every
output area against every other, and there is no public file of the non-zero ones. All of England and Wales, 2011 boundaries; see
incoming.ons_census_area_lookup_2011_2021 to compare with 2021 areas. Static: load once.

Usage:
    python nomis_census_2011/nomis_census_2011_load.py
    python nomis_census_2011/nomis_census_2011_load.py --table nomis_census_2011_commute_flows
"""

import argparse
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"
BULK_URL = "https://www.nomisweb.co.uk/api/v01/dataset/{dataset}.bulk.csv"

# Method of travel categories, in Nomis column order; QS701EW adds "Not in employment"
METHODS = ["all_methods", "work_from_home", "underground_metro_tram", "train", "bus_coach", "taxi", "motorcycle",
           "car_driver", "car_passenger", "bicycle", "on_foot", "other"]
METHOD_LABELS = ["All categories", "Work mainly at or from home", "Underground", "Train", "Bus", "Taxi", "Motorcycle",
                 "Driving a car or van", "Passenger in a car or van", "Bicycle", "On foot", "Other method"]

# geography_level -> Nomis area type
TRAVEL_METHOD_LEVELS = {"oa": "TYPE299", "lsoa": "TYPE298", "msoa": "TYPE297", "ward": "TYPE295", "ltla": "TYPE464"}
# WU03EW by MSOA: the ONS file of non-zero flows, as archived by Jisc for the UK Data Service. (Nomis's whole-table
# download is every MSOA against every area, 54 million rows, 96% zeros.)
WU03EW_MSOA_URL = ("https://s3-eu-west-1.amazonaws.com/statistics.digitalresources.jisc.ac.uk/dkan/files/FLOW/"
                   "wu03ew_v2/wu03ew_v2.zip")
MSOA11_NAMES_URL = ("https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
                    "MSOA11_MSOA21_LAD22_EW_LU_v2/FeatureServer/0/query")
# Place of work codes that aren't areas
SPECIAL_WORKPLACES = {"OD0000001": "Mainly work at or from home", "OD0000002": "Offshore installation",
                      "OD0000003": "No fixed place", "OD0000004": "Outside UK",
                      "S92000003": "Scotland", "N92000002": "Northern Ireland"}
# Nomis place_of_work values for the first four, and census merged local authorities (City of London with
# Westminster, Isles of Scilly with Cornwall)
LTLA_WORKPLACES = "1103101953...1103101956,TYPE270"


def bulk_csv(dataset, params, path):
    """Stream a Nomis whole-table CSV to path and read it (all columns as strings)."""
    with requests.get(BULK_URL.format(dataset=dataset), params={"time": "latest", "measures": "20100", **params},
                      stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(16 << 20):
                f.write(chunk)
    with open(path) as f:
        if f.read(6) == "Error:":
            raise RuntimeError(f"Nomis {dataset} {params}: {open(path).read(200)}")
    return pd.read_csv(path, dtype=str)


def method_columns(df, first, labels):
    """Rename the count columns starting at index `first`, checking they are in the expected category order."""
    counts = list(df.columns[first:])
    if len(counts) != len(labels) or not all(label.lower() in c.lower() for label, c in zip(labels, counts)):
        raise ValueError(f"Unexpected categories: {counts}")
    return dict(zip(counts, METHODS + ["not_in_employment"]))


def write(df, table, level):
    with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
        df.to_parquet(tmp.name, index=False, compression="zstd")
        load_file_to_s3(tmp.name, S3_INCOMING_BUCKET, f"{table}/geography_level={level}/{table}_{level}.parquet")
    add_glue_partition("geography_level", level, table, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
    print(f"  {level}: {len(df):,} rows")


def load_travel_method():
    table = "nomis_census_2011_travel_method"
    for level, area_type in TRAVEL_METHOD_LEVELS.items():
        with tempfile.TemporaryDirectory() as tmp:
            df = bulk_csv("nm_568_1", {"geography": area_type, "rural_urban": "0"}, Path(tmp) / "qs701ew.csv")
        df = df.rename(columns={"geography code": "geography_code", "geography": "geography_name"})
        df = df.rename(columns=method_columns(df, 4, METHOD_LABELS + ["Not in employment"]))
        columns = METHODS + ["not_in_employment"]
        df = df[["geography_code", "geography_name"] + columns]
        df[columns] = df[columns].astype("int32")
        write(df, table, level)


def msoa11_names():
    names, offset = {}, 0
    while True:
        page = requests.get(MSOA11_NAMES_URL, timeout=120, params={
            "where": "1=1", "outFields": "MSOA11CD,MSOA11NM", "returnGeometry": "false",
            "resultOffset": offset, "resultRecordCount": 1000, "f": "json"}).json()["features"]
        names.update((f["attributes"]["MSOA11CD"], f["attributes"]["MSOA11NM"]) for f in page)
        if len(page) < 1000:
            return names
        offset += len(page)


def msoa_flows(tmp):
    zip_path = Path(tmp) / "wu03ew_v2.zip"
    with requests.get(WU03EW_MSOA_URL, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(16 << 20):
                f.write(chunk)
    with zipfile.ZipFile(zip_path) as zf, zf.open("wu03ew_v2.csv") as f:
        df = pd.read_csv(f, dtype={"Area of residence": str, "Area of workplace": str})
    df = df.rename(columns={"Area of residence": "home_code", "Area of workplace": "workplace_code"})
    df = df.rename(columns=method_columns(df, 2, METHOD_LABELS))
    names = {**msoa11_names(), **SPECIAL_WORKPLACES}
    df["home_name"] = df["home_code"].map(names)
    df["workplace_name"] = df["workplace_code"].map(names)
    return df


def ltla_flows(tmp):
    df = bulk_csv("nm_1208_1", {"usual_residence": "TYPE270", "place_of_work": LTLA_WORKPLACES}, Path(tmp) / "wu03ew.csv")
    df = df.rename(columns={"usual residence code": "home_code", "usual residence": "home_name",
                            "place of work code": "workplace_code", "place of work": "workplace_name"})
    return df.rename(columns=method_columns(df, 5, METHOD_LABELS))


def load_commute_flows():
    table = "nomis_census_2011_commute_flows"
    for level, fetch in (("msoa", msoa_flows), ("ltla", ltla_flows)):
        with tempfile.TemporaryDirectory() as tmp:
            df = fetch(tmp)
        df = df[["home_code", "home_name", "workplace_code", "workplace_name"] + METHODS]
        df[METHODS] = df[METHODS].apply(pd.to_numeric).astype("int32")
        df = df[df["all_methods"] > 0]
        missing = df["home_name"].isna().sum() + df["workplace_name"].isna().sum()
        if missing:
            print(f"  {level}: {missing} codes without a name")
        write(df, table, level)


TABLES = {"nomis_census_2011_travel_method": load_travel_method,
          "nomis_census_2011_commute_flows": load_commute_flows}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", choices=list(TABLES))
    args = parser.parse_args()
    for t in [args.table] if args.table else TABLES:
        print(f"Loading {t}...")
        TABLES[t]()
