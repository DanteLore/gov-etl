"""
Load National Highways WebTRIS traffic counts into S3: 15-minute vehicle counts by length band, speed bands
and average speed at the active count sites on the M4 (junctions 12 to 14) and the A34 (Chieveley to the A343)
around Newbury and Thatcham, as far back as the API holds (about 2017 for most sites).

Source: webtris.nationalhighways.co.uk/api/v1.0, the Daily report (15-minute rows). Data arrives a few months
in arrears; rerun to refresh the current year (each site-year file is replaced). Also loads the full site list.

Nationally, the Monthly report gives each site's daily flow and its average hourly flow by weekday for every
WebTRIS site in England (active and inactive), 25 sites per request. The 15-minute data isn't loaded nationally:
it would be about 1.5 TB of API downloads.

Tables:
    incoming.webtris_sites             every WebTRIS site in England, with location and status
    incoming.webtris_counts            15-minute counts for the sites in the area, partitioned by year
    incoming.webtris_daily_flows       daily flow and large vehicle share, every site, partitioned by year
    incoming.webtris_hourly_profiles   average flow per hour by weekday and month, every site, partitioned by year

Usage:
    python webtris/webtris_load.py                          # 15-minute counts for the area, all years
    python webtris/webtris_load.py --from-year 2026
    python webtris/webtris_load.py --national               # daily flows and hourly profiles, every site
    python webtris/webtris_load.py --national --from-year 2026
"""

import argparse
import calendar
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
SITES_PER_REQUEST = 25
HOURS = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
         "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen", "Twenty", "TwentyOne", "TwentyTwo",
         "TwentyThree", "TwentyFour"]
MONTHS = {name: number for number, name in enumerate(calendar.month_name) if name}

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


def _number(value, kind=int):
    return kind(value) if value not in (None, "") else None


def get_with_retry(url, params, attempts=4):
    """GET, retrying WebTRIS's occasional 5xx errors and dropped connections with a growing pause."""
    for attempt in range(1, attempts + 1):
        try:
            r = requests.get(url, params=params, timeout=300)
            if r.status_code < 500:
                return r
        except (requests.ConnectionError, requests.Timeout):
            if attempt == attempts:
                raise
        if attempt == attempts:
            r.raise_for_status()
        time.sleep(30 * attempt)


def fetch_monthly(site_ids, year):
    """The Monthly report for a batch of sites and a year: (daily rows, hourly profile rows), or None if no data."""
    end = min(date(year, 12, 31), date.today())
    months, page = [], 1
    while True:
        r = get_with_retry(f"{API}/reports/Monthly", params={
            "sites": ",".join(site_ids), "start_date": f"0101{year}", "end_date": end.strftime("%d%m%Y"),
            "page": page, "page_size": 40000})
        if page == 1 and (r.status_code in (204, 400) or not r.content):
            return None
        r.raise_for_status()
        body = r.json()
        months.extend(body.get("MonthCollection", []))
        if not any(link.get("rel") == "nextPage" for link in body["Header"].get("links", [])):
            break
        page += 1
    daily, hourly = [], []
    for m in months:
        name, month_year = m["Month"].split(" ")
        month = date(int(month_year), MONTHS[name], 1)
        for d in m["Days"]:
            daily.append({"site_id": m["SiteId"], "report_date": month.replace(day=int(d["DayNumber"])),
                          "day_name": d["DayName"], "flow": _number(d["FlowValue"]),
                          "large_vehicle_pct": _number(d["LargeVehiclePercentage"], float)})
        by_day = {a["DayName"]: a for a in m.get("Daily Aggregations", [])}
        for h in m.get("Hourly Aggregations", []):
            agg = by_day.get(h["DayName"], {})
            for i, hour in enumerate(HOURS):
                hourly.append({"site_id": m["SiteId"], "month_start": month, "day_name": h["DayName"], "hour_start": i,
                               "average_vehicles": _number(h.get(f"Hour{hour}Total")),
                               "days_averaged": _number(agg.get("NumberOfDays"), float),
                               "average_flow_24h": _number(agg.get("AverageFlow24")),
                               "large_vehicle_pct_24h": _number(agg.get("PercentageOfLargeVehiclesIn24Hours"), float)})
    return daily, hourly


def fetch_batch(site_ids, year):
    """Monthly report results for a batch of sites. Some sites make WebTRIS fail with a 500 for the whole batch,
    so if the batch keeps failing, fetch its sites one at a time and skip the ones that still fail."""
    try:
        result = fetch_monthly(site_ids, year)
        time.sleep(0.5)
        return [result] if result else []
    except requests.HTTPError:
        print(f"    {year}: batch from site {site_ids[0]} failed, fetching its sites one at a time")
    results = []
    for site_id in site_ids:
        try:
            result = fetch_monthly([site_id], year)
            if result:
                results.append(result)
        except requests.HTTPError as e:
            print(f"    {year}: skipped site {site_id} ({e.response.status_code})")
        time.sleep(0.5)
    return results


def load_national(from_year):
    sites = load_sites()
    site_ids = list(sites.site_id)
    for year in range(from_year, date.today().year + 1):
        # Frames per batch rather than one big list of dicts: a year of hourly profiles is about 30 million rows
        daily, hourly = [], []
        for i in range(0, len(site_ids), SITES_PER_REQUEST):
            for result in fetch_batch(site_ids[i:i + SITES_PER_REQUEST], year):
                daily.append(pd.DataFrame(result[0]))
                hourly.append(pd.DataFrame(result[1]))
        if not daily:
            print(f"  {year}: no data")
            continue
        for table, frames in (("webtris_daily_flows", daily), ("webtris_hourly_profiles", hourly)):
            df = pd.concat(frames, ignore_index=True)
            for col in ("flow", "average_vehicles", "average_flow_24h", "hour_start"):
                if col in df.columns:
                    df[col] = df[col].astype("Int32")
            with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
                df.to_parquet(tmp.name, index=False, compression="zstd")
                load_file_to_s3(tmp.name, S3_INCOMING_BUCKET, f"webtris/{table.removeprefix('webtris_')}/year={year}/{table}_{year}.parquet")
            add_glue_partition_y(year, table, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
        print(f"  {year}: {pd.concat(daily).site_id.nunique():,} sites with data")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-year", type=int, default=FIRST_YEAR)
    parser.add_argument("--national", action="store_true", help="Daily flows and hourly profiles for every site")
    args = parser.parse_args()
    if args.national:
        load_national(args.from_year)
    else:
        load(args.from_year)
