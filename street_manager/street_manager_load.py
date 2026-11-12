"""
Load Street Manager (DfT roadworks service) permit events for West Berkshire into S3: every permit submitted,
granted, refused or cancelled, and every works start and stop, by utilities and the highway authority.

Source: the Street Manager open data monthly archives (opendata.manage-roadworks.service.gov.uk/permit/YYYY/MM.zip,
about 1 GB and a million JSON events each, all of England, from 2021). Only events whose highway authority is
West Berkshire Council (SWA code 340) are kept. One row per event, with the common permit fields as columns and
the whole object_data as JSON. Partitioned by event_month; a month's file is replaced when reloaded.

Usage:
    python street_manager/street_manager_load.py                      # every month not yet loaded
    python street_manager/street_manager_load.py --month 2026-10      # reload one month
"""

import argparse
import json
import struct
import sys
import zlib
import tempfile
import zipfile
from datetime import date
from pathlib import Path

import boto3
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"
TABLE = "street_manager_permit_events"
PREFIX = "street_manager/permit_events/"
URL = "https://opendata.manage-roadworks.service.gov.uk/permit/{year}/{month:02d}.zip"
FIRST_MONTH = date(2020, 7, 1)
SWA_CODE = "340"  # West Berkshire Council
MATCH = f'"highway_authority_swa_code":"{SWA_CODE}"'.encode()

FIELDS = ["work_reference_number", "permit_reference_number", "promoter_swa_code", "promoter_organisation",
          "highway_authority", "highway_authority_swa_code", "works_location_coordinates", "street_name", "area_name",
          "town", "usrn", "road_category", "is_traffic_sensitive", "work_category", "activity_type",
          "traffic_management_type", "works_location_type", "is_ttro_required", "work_status", "permit_status",
          "proposed_start_date", "proposed_start_time", "proposed_end_date", "proposed_end_time",
          "actual_start_date_time", "actual_end_date_time", "permit_conditions", "close_footway",
          "collaborative_working", "is_deemed"]


def months(start):
    today = date.today()
    current = start
    while current < date(today.year, today.month, 1):
        yield current
        current = date(current.year + current.month // 12, current.month % 12 + 1, 1)


def loaded_months():
    s3 = boto3.client("s3")
    pages = s3.get_paginator("list_objects_v2").paginate(Bucket=S3_INCOMING_BUCKET, Prefix=f"{PREFIX}event_month=", Delimiter="/")
    return {p["Prefix"].rstrip("/").split("=", 1)[1] for page in pages for p in page.get("CommonPrefixes", [])}


def zip_members(zip_path):
    """Yield each member's bytes. Most archives are normal zips, but many from 2020 to 2025 are streamed zips
    with no central directory, so those are read entry by entry from their local headers."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                yield zf.read(name)
        return
    except zipfile.BadZipFile:
        pass
    data = memoryview(Path(zip_path).read_bytes())
    pos = 0
    while data[pos:pos + 4] == b"PK\x03\x04":
        _, _, flag, method, _, _, _, _, _, name_len, extra_len = struct.unpack("<IHHHHHIIIHH", data[pos:pos + 30])
        if method != 8:
            raise ValueError(f"Unexpected compression method {method} at byte {pos}")
        # Inflate in small chunks until the deflate stream ends, which is where the entry ends
        inflater, parts, offset = zlib.decompressobj(-15), [], pos + 30 + name_len + extra_len
        while not inflater.eof and offset < len(data):
            chunk = data[offset:offset + 65536]
            parts.append(inflater.decompress(chunk))
            offset += len(chunk)
        if not inflater.eof:
            return  # the last entry is cut off
        pos = offset - len(inflater.unused_data)
        if flag & 8:  # data descriptor, with or without its signature
            pos += 16 if data[pos:pos + 4] == b"PK\x07\x08" else 12
        yield b"".join(parts)


def month_events(zip_path):
    rows = []
    for body in zip_members(zip_path):
        if MATCH not in body:
            continue
        event = json.loads(body)
        data = event["object_data"]
        row = {"event_reference": event["event_reference"], "event_type": event["event_type"],
               "event_time": event["event_time"], "object_type": event["object_type"],
               "object_reference": event["object_reference"], "version": event.get("version")}
        row.update({f: None if data.get(f) is None else str(data.get(f)) for f in FIELDS})
        row["object_data_json"] = json.dumps(data)
        rows.append(row)
    df = pd.DataFrame(rows, columns=["event_reference", "event_type", "event_time", "object_type", "object_reference",
                                     "version"] + FIELDS + ["object_data_json"])
    df["event_time"] = pd.to_datetime(df["event_time"], utc=True).dt.tz_localize(None)
    df["event_reference"] = df["event_reference"].astype("int64")
    df["version"] = df["version"].astype("Int32")
    return df


def load_month(month):
    label = f"{month:%Y-%m}"
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / f"{label}.zip"
        with requests.get(URL.format(year=month.year, month=month.month), stream=True, timeout=600) as r:
            if r.status_code == 404:
                print(f"  {label}: no archive")
                return
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(16 << 20):
                    f.write(chunk)
        df = month_events(zip_path)
        out = Path(tmp) / f"{TABLE}_{label}.parquet"
        df.to_parquet(out, index=False)
        load_file_to_s3(str(out), S3_INCOMING_BUCKET, f"{PREFIX}event_month={label}/{TABLE}_{label}.parquet")
    add_glue_partition("event_month", label, TABLE, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
    print(f"  {label}: {len(df):,} West Berkshire events")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", help="YYYY-MM to (re)load")
    args = parser.parse_args()
    if args.month:
        load_month(date.fromisoformat(f"{args.month}-01"))
    else:
        done = loaded_months()
        for m in months(FIRST_MONTH):
            if f"{m:%Y-%m}" not in done:
                load_month(m)
