"""
Load National Highways WebTRIS traffic counts into S3: 15-minute vehicle counts by length band, speed bands
and average speed at the active count sites on the M4 (junctions 12 to 14) and the A34 (Chieveley to the A343)
around Newbury and Thatcham, as far back as the API holds (about 2017 for most sites).

Source: webtris.nationalhighways.co.uk/api/v1.0, the Daily report (15-minute rows). Data arrives a few months
in arrears; rerun to refresh the current year (each site-year file is replaced). Also loads the full site list.

Tables:
    incoming.webtris_sites    every WebTRIS site in England, with location and status
    incoming.webtris_counts   15-minute counts for the sites in the area, partitioned by year

Usage:
    python webtris/webtris_load.py                 # all years
    python webtris/webtris_load.py --from-year 2026
"""

import argparse
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition_y

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"
API = "https://webtris.nationalhighways.co.uk/api/v1.0"
FIRST_YEAR = 2010

# M4 junctions 12-14 and the A34 between Chieveley and the A343
MIN_LAT, MAX_LAT = 51.36, 51.50
MIN_LON, MAX_LON = -1.40, -1.05

COLUMNS = {
    "Site Name": "site_name", "Report Date": "report_date", "Time Period Ending": "time_period_ending",
    "Time Interval": "time_interval",
    "0 - 520 cm": "vehicles_0_520cm", "521 - 660 cm": "vehicles_521_660cm", "661 - 1160 cm": "vehicles_661_1160cm",
    "1160+ cm": "vehicles_over_1160cm",
    "0 - 10 mph": "vehicles_0_10mph", "11 - 15 mph": "vehicles_11_15mph", "16 - 20 mph": "vehicles_16_20mph",
    "21 - 25 mph": "vehicles_21_25mph", "26 - 30 mph": "vehicles_26_30mph", "31 - 35 mph": "vehicles_31_35mph",
    "36 - 40 mph": "vehicles_36_40mph", "41 - 45 mph": "vehicles_41_45mph", "46 - 50 mph": "vehicles_46_50mph",
    "51 - 55 mph": "vehicles_51_55mph", "56 - 60 mph": "vehicles_56_60mph", "61 - 70 mph": "vehicles_61_70mph",
    "71 - 80 mph": "vehicles_71_80mph", "80+ mph": "vehicles_over_80mph",
    "Avg mph": "avg_mph", "Total Volume": "total_volume",
}


def load_sites():
    sites = pd.DataFrame(requests.get(f"{API}/sites", timeout=120).json()["sites"])
    sites = sites.rename(columns={"Id": "site_id", "Name": "site_name", "Description": "description",
                                  "Longitude": "longitude", "Latitude": "latitude", "Status": "status"})
    sites = sites[["site_id", "site_name", "description", "longitude", "latitude", "status"]]
    with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
        sites.to_parquet(tmp.name, index=False)
        load_file_to_s3(tmp.name, S3_INCOMING_BUCKET, "webtris/sites/webtris_sites.parquet")
    print(f"{len(sites):,} sites")
    return sites


def fetch_year(site_id, year):
    """All 15-minute rows for a site and year, or None if the API has none."""
    end = min(date(year, 12, 31), date.today())
    rows, page = [], 1
    while True:
        r = requests.get(f"{API}/reports/Daily", timeout=300, params={
            "sites": site_id, "start_date": f"0101{year}", "end_date": end.strftime("%d%m%Y"),
            "page": page, "page_size": 40000})
        if page == 1 and (r.status_code in (204, 400) or not r.content):
            return None  # no data for this site in the range (400 or an empty reply)
        r.raise_for_status()
        body = r.json()
        rows.extend(body["Rows"])
        if not any(link.get("rel") == "nextPage" for link in body["Header"].get("links", [])):
            break
        page += 1
    df = pd.DataFrame(rows).rename(columns=COLUMNS)[list(COLUMNS.values())]
    df.insert(0, "site_id", str(site_id))
    df["report_date"] = pd.to_datetime(df["report_date"]).dt.date
    for col in df.columns[5:]:
        df[col] = pd.to_numeric(df[col].replace("", None), errors="coerce").astype("Int32")
    df["time_interval"] = df["time_interval"].astype("int32")
    return df


def load(from_year):
    sites = load_sites()
    area = sites[(sites.status == "Active") & sites.latitude.between(MIN_LAT, MAX_LAT) & sites.longitude.between(MIN_LON, MAX_LON)]
    print(f"{len(area)} active sites in the area")
    for year in range(from_year, date.today().year + 1):
        loaded = 0
        for site_id in area.site_id:
            df = fetch_year(site_id, year)
            time.sleep(0.5)
            if df is None or df["total_volume"].isna().all():
                continue
            with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
                df.to_parquet(tmp.name, index=False)
                load_file_to_s3(tmp.name, S3_INCOMING_BUCKET, f"webtris/counts/year={year}/webtris_counts_{year}_site_{site_id}.parquet")
            loaded += 1
        if loaded:
            add_glue_partition_y(year, "webtris_counts", ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
        print(f"  {year}: {loaded} sites with data")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-year", type=int, default=FIRST_YEAR)
    args = parser.parse_args()
    load(args.from_year)
