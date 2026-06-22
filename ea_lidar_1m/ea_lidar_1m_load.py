"""
Load Environment Agency 1m LiDAR Composite DTM into S3, partitioned by 100km OSGB grid tile.

Fetches bare-earth elevation data for England from the EA WCS endpoint, requesting one
10km x 10km bounding box at a time as a GeoTIFF. Each 10km chunk yields up to 10,000 x 10,000
= 100M points at 1m resolution, stored as one Parquet file under the appropriate 100km partition.

Each row written to S3 represents the SW corner of one 1m cell:
    x_coordinate, y_coordinate  -- OSGB36 coordinates (EPSG:27700)
    elevation_m                 -- metres above sea level (bare earth, voids filled)

Partition keys (matching os_open_uprn):
    grid_e  -- floor(x_coordinate / 100000), 100km easting tile index (0-6)
    grid_n  -- floor(y_coordinate / 100000), 100km northing tile index (0-12)

Usage:
    python ea_lidar_1m/ea_lidar_1m_load.py              # full England run
    python ea_lidar_1m/ea_lidar_1m_load.py --bbox 530000,180000,540000,190000
"""

import argparse
import io
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition_en

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"

WCS_URL = "https://environment.data.gov.uk/geoservices/datasets/13787b9a-26a4-4775-8523-806d13af58fc/wcs"
COVERAGE_ID = "13787b9a-26a4-4775-8523-806d13af58fc__Lidar_Composite_Elevation_DTM_1m"

TMP_TIFF = "/tmp/ea_lidar_1m_chunk.tif"
TMP_PARQUET = "/tmp/ea_lidar_1m_chunk.parquet"

# 10km step across England's OSGB36 bounding box
# England: roughly E 0–700000, N 0–700000 (GB extent)
STEP = 10_000
E_MIN, E_MAX = 0, 700_000
N_MIN, N_MAX = 0, 700_000


def fetch_chunk(min_e: int, min_n: int) -> bytes | None:
    """Request a 10km x 10km GeoTIFF from the WCS. Returns None if no data."""
    max_e = min_e + STEP
    max_n = min_n + STEP
    # WCS 2.0 uses subset parameters, not BoundingBox
    params = [
        ("service", "WCS"),
        ("version", "2.0.1"),
        ("request", "GetCoverage"),
        ("coverageId", COVERAGE_ID),
        ("subset", f"E,urn:ogc:def:crs:EPSG::27700({min_e},{max_e})"),
        ("subset", f"N,urn:ogc:def:crs:EPSG::27700({min_n},{max_n})"),
        ("format", "image/tiff"),
    ]
    resp = requests.get(WCS_URL, params=params, timeout=120)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    if b"ExceptionReport" in resp.content[:500] or b"<?xml" in resp.content[:20]:
        print(f"\n  WCS error: {resp.content[:300].decode(errors='replace')}")
        return None
    return resp.content


def tiff_to_dataframe(tiff_bytes: bytes) -> pd.DataFrame:
    """Convert a GeoTIFF to a DataFrame of (x_coordinate, y_coordinate, elevation_m)."""
    with rasterio.open(io.BytesIO(tiff_bytes)) as src:
        data = src.read(1).astype(np.float32)
        nodata = src.nodata
        transform = src.transform
        nrows, ncols = data.shape

    row_idx, col_idx = np.meshgrid(np.arange(nrows), np.arange(ncols), indexing="ij")
    # transform maps pixel (col, row) to (x, y) — top-left corner of each cell
    xs = (transform.c + col_idx * transform.a).astype(np.int32)
    ys = (transform.f + row_idx * transform.e).astype(np.int32)

    elevs = data.ravel()
    mask = (elevs != nodata) & np.isfinite(elevs)

    return pd.DataFrame({
        "x_coordinate": xs.ravel()[mask],
        "y_coordinate": ys.ravel()[mask],
        "elevation_m": elevs[mask],
    })


def process_chunk(min_e: int, min_n: int) -> int:
    """Fetch, parse, and upload one 10km chunk. Returns row count."""
    tiff_bytes = fetch_chunk(min_e, min_n)
    if tiff_bytes is None:
        return 0

    df = tiff_to_dataframe(tiff_bytes)
    if df.empty:
        return 0

    grid_e = min_e // 100_000
    grid_n = min_n // 100_000

    df.to_parquet(TMP_PARQUET, index=False)

    chunk_label = f"e{min_e}_n{min_n}"
    s3_key = f"ea_lidar_1m/dtm/grid_e={grid_e}/grid_n={grid_n}/dtm_{chunk_label}.parquet"
    load_file_to_s3(TMP_PARQUET, S3_INCOMING_BUCKET, s3_key)
    add_glue_partition_en(grid_e, grid_n, "ea_lidar_1m_dtm", ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)

    return len(df)


def iter_chunks(bbox: tuple[int, int, int, int] | None):
    """Yield (min_e, min_n) for every 10km chunk in the given bbox or full England extent."""
    min_e, min_n, max_e, max_n = bbox if bbox else (E_MIN, N_MIN, E_MAX, N_MAX)
    for n in range(min_n, max_n, STEP):
        for e in range(min_e, max_e, STEP):
            yield e, n


def load(bbox: tuple[int, int, int, int] | None = None):
    chunks = list(iter_chunks(bbox))
    total_rows = 0
    for i, (min_e, min_n) in enumerate(chunks, 1):
        label = f"E{min_e} N{min_n}"
        print(f"[{i}/{len(chunks)}] {label}...", end=" ", flush=True)
        try:
            n = process_chunk(min_e, min_n)
            if n:
                print(f"{n:,} points")
                total_rows += n
            else:
                print("no data")
        except Exception as e:
            print(f"ERROR: {e}")

    print(f"Done. {total_rows:,} total points.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bbox",
        help="Bounding box as min_e,min_n,max_e,max_n in OSGB36 metres (e.g. 530000,180000,540000,190000)",
    )
    args = parser.parse_args()

    bbox = None
    if args.bbox:
        parts = [int(x) for x in args.bbox.split(",")]
        bbox = (parts[0], parts[1], parts[2], parts[3])

    load(bbox=bbox)
