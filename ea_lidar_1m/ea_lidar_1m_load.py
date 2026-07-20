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
import time
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

# A full 10km x 10km chunk at 1m resolution is 10,000 x 10,000 pixels. Observed WCS
# response times for a full chunk are ~150-170s. The WCS endpoint has also been observed
# to stall indefinitely mid-response (connection stays open, no bytes, no error) — the
# `requests` timeout does not catch this since it only bounds connect time and gaps
# between individual reads, not a slow trickle. STALL_TIMEOUT below bounds the gap
# between successive chunks of received bytes; FETCH_WALL_CLOCK_TIMEOUT bounds the total
# time for one fetch regardless of how the server behaves.
STALL_TIMEOUT = 60
FETCH_WALL_CLOCK_TIMEOUT = 400
FETCH_RETRIES = 3
RETRY_BACKOFF_SECONDS = 10


def fetch_chunk(min_e: int, min_n: int) -> bytes | None:
    """Request a 10km x 10km GeoTIFF from the WCS. Returns None if no data. Retries on transient failure."""
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

    last_error = None
    for attempt in range(1, FETCH_RETRIES + 1):
        try:
            start = time.monotonic()
            chunks = []
            with requests.get(WCS_URL, params=params, timeout=STALL_TIMEOUT, stream=True) as resp:
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                for piece in resp.iter_content(chunk_size=1024 * 1024):
                    if time.monotonic() - start > FETCH_WALL_CLOCK_TIMEOUT:
                        raise TimeoutError(
                            f"fetch exceeded {FETCH_WALL_CLOCK_TIMEOUT}s wall-clock limit"
                        )
                    chunks.append(piece)
            content = b"".join(chunks)
            if b"ExceptionReport" in content[:500] or b"<?xml" in content[:20]:
                print(f"\n  WCS error: {content[:300].decode(errors='replace')}")
                return None
            return content
        except (requests.exceptions.RequestException, TimeoutError, OSError) as e:
            last_error = e
            if attempt < FETCH_RETRIES:
                print(f"\n  fetch failed (attempt {attempt}/{FETCH_RETRIES}): {e} — retrying...", end=" ", flush=True)
                time.sleep(RETRY_BACKOFF_SECONDS)

    raise RuntimeError(f"WCS fetch failed after {FETCH_RETRIES} attempts: {last_error}")


def tiff_to_dataframe(tiff_bytes: bytes) -> tuple[pd.DataFrame, int]:
    """Convert a GeoTIFF to a DataFrame of (x_coordinate, y_coordinate, elevation_m).

    Returns the DataFrame plus the total pixel count in the source raster, so callers
    can detect a truncated/short TIFF (fewer pixels than a full chunk) independently of
    legitimate nodata voids (which are excluded from the DataFrame but still counted here).
    """
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

    df = pd.DataFrame({
        "x_coordinate": xs.ravel()[mask],
        "y_coordinate": ys.ravel()[mask],
        "elevation_m": elevs[mask],
    })
    return df, nrows * ncols


# A full 10km x 10km chunk at 1m resolution is exactly this many pixels.
EXPECTED_CHUNK_PIXELS = STEP * STEP


def process_chunk(min_e: int, min_n: int) -> int:
    """Fetch, parse, and upload one 10km chunk. Returns row count.

    Raises if the source TIFF has fewer pixels than a full chunk, since that indicates
    a truncated/short response rather than legitimate nodata voids (voids are already
    excluded from the row count by tiff_to_dataframe and are not an error).
    """
    tiff_bytes = fetch_chunk(min_e, min_n)
    if tiff_bytes is None:
        return 0

    df, pixel_count = tiff_to_dataframe(tiff_bytes)
    if pixel_count != EXPECTED_CHUNK_PIXELS:
        raise RuntimeError(
            f"short TIFF for chunk e{min_e}_n{min_n}: got {pixel_count:,} pixels, "
            f"expected {EXPECTED_CHUNK_PIXELS:,}"
        )
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
    failed_chunks = []
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
            failed_chunks.append((min_e, min_n))

    print(f"Done. {total_rows:,} total points.")
    if failed_chunks:
        print(f"\n{len(failed_chunks)} chunk(s) FAILED and were not loaded:")
        for min_e, min_n in failed_chunks:
            print(f"  --bbox {min_e},{min_n},{min_e + STEP},{min_n + STEP}")
        print("Re-run the loader with one of the bboxes above to retry a failed chunk.")


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
