"""
Load OS Code Point Open data into S3, partitioned by postcode area.

Downloads the current release ZIP from the OS Data Hub (no authentication required).
The archive contains 120 CSV files (one per postcode area, e.g. ab.csv, sw.csv) with
no column headers. Column names are taken from the bundled header file.

Partition key:
    postcode_area  -- two-letter postcode area code derived from the CSV filename (e.g. 'sw')

Usage:
    python os_code_point_open/os_code_point_open_load.py
"""

import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition_area

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"

API_URL = "https://api.os.uk/downloads/v1/products/CodePointOpen/downloads"
DOWNLOAD_URL = f"{API_URL}?area=GB&format=CSV&redirect"

COLUMNS = [
    "postcode",
    "positional_quality_indicator",
    "eastings",
    "northings",
    "country_code",
    "nhs_regional_ha_code",
    "nhs_ha_code",
    "admin_county_code",
    "admin_district_code",
    "admin_ward_code",
]

TMP_PARQUET = "/tmp/os_code_point_open_area.parquet"


def fetch_zip_bytes() -> bytes:
    print("Fetching current release info...")
    releases = requests.get(API_URL, timeout=30)
    releases.raise_for_status()
    filename = next(r["fileName"] for r in releases.json() if r["format"] == "CSV")
    print(f"  Current release: {filename}")

    print(f"Downloading {DOWNLOAD_URL}")
    response = requests.get(DOWNLOAD_URL, stream=True, timeout=600)
    response.raise_for_status()
    return response.content


def load():
    zip_bytes = fetch_zip_bytes()

    print("Processing CSVs from zip...")
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        csv_names = sorted(n for n in zf.namelist() if n.startswith("Data/CSV/") and n.endswith(".csv"))
        print(f"  {len(csv_names)} postcode area files")

        for csv_name in csv_names:
            postcode_area = Path(csv_name).stem.lower()

            with zf.open(csv_name) as f:
                df = pd.read_csv(
                    f,
                    header=None,
                    names=COLUMNS,
                    dtype={
                        "postcode": str,
                        "positional_quality_indicator": "Int64",
                        "eastings": "Int64",
                        "northings": "Int64",
                        "country_code": str,
                        "nhs_regional_ha_code": str,
                        "nhs_ha_code": str,
                        "admin_county_code": str,
                        "admin_district_code": str,
                        "admin_ward_code": str,
                    },
                )

            df.to_parquet(TMP_PARQUET, index=False)

            s3_key = f"os_code_point_open/codepo/postcode_area={postcode_area}/codepo_{postcode_area}.parquet"
            load_file_to_s3(TMP_PARQUET, S3_INCOMING_BUCKET, s3_key)
            add_glue_partition_area(postcode_area, "os_code_point_open_codepo", ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
            print(f"  Area {postcode_area}: {len(df):,} rows")

    print("Done.")


if __name__ == "__main__":
    load()
