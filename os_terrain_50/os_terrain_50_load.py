"""
Load OS Terrain 50 elevation data into S3, partitioned by 100km OSGB grid tile.

Downloads the full GB dataset from the OS Data Hub (no authentication required).
The archive contains ~2,500 ASC files, one per 10km tile (e.g. NY30.asc), each
holding a 200x200 grid of elevation values at 50m resolution.

Each row written to S3 represents the SW corner of one 50m cell:
    x_coordinate, y_coordinate  -- OSGB36 coordinates (EPSG:27700)
    elevation_m                 -- metres above sea level

Partition keys (matching os_open_uprn):
    grid_e  -- floor(x_coordinate / 100000), 100km easting tile index (0-6)
    grid_n  -- floor(y_coordinate / 100000), 100km northing tile index (0-12)

Usage:
    python os_terrain_50/os_terrain_50_load.py
"""

import sys
import tempfile
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition_en
from helpers.terrain import parse_asc

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"

API_URL = "https://api.os.uk/downloads/v1/products/Terrain50/downloads"
DOWNLOAD_URL = f"{API_URL}?area=GB&format=ASCII+Grid+and+GML+%28Grid%29&redirect"

TMP_PARQUET = "/tmp/os_terrain_50_tile.parquet"
CACHE_DIR = Path(tempfile.gettempdir()) / "gov_etl_cache"


def fetch_zip(cache_path: Path) -> Path:
    print("Fetching current release info...")
    releases = requests.get(API_URL, timeout=30)
    releases.raise_for_status()
    filename = next(
        r["fileName"] for r in releases.json()
        if "ASCII" in r.get("format", "") or r.get("format", "") == "ASCII Grid and GML (Grid)"
    )
    print(f"  Current release: {filename}")

    if cache_path.exists():
        print(f"  Using cached zip: {cache_path}")
        return cache_path

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading to {cache_path}...")
    response = requests.get(DOWNLOAD_URL, stream=True, timeout=1800)
    response.raise_for_status()
    cache_path.write_bytes(response.content)
    return cache_path


def load():
    cache_path = CACHE_DIR / "os_terrain_50.zip"
    fetch_zip(cache_path)

    # The outer ZIP contains one inner ZIP per tile (e.g. data/hp/hp40_OST50GRID_*.zip)
    # Each inner ZIP contains TILENAME.asc at its root
    print("Processing ASC tiles from zip...")
    with zipfile.ZipFile(cache_path) as outer:
        inner_zip_names = sorted(n for n in outer.namelist() if n.lower().endswith(".zip"))
        print(f"  {len(inner_zip_names)} tile files")

        for inner_zip_name in inner_zip_names:
            tile = Path(inner_zip_name).stem.split("_")[0].lower()

            with outer.open(inner_zip_name) as inner_bytes:
                with zipfile.ZipFile(inner_bytes) as inner:
                    asc_name = next(n for n in inner.namelist() if n.lower().endswith(".asc"))
                    with inner.open(asc_name) as raw:
                        df = parse_asc(raw.read())

            if df.empty:
                print(f"  Tile {tile}: empty (all nodata), skipping")
                continue

            df = df.rename(columns={"easting": "x_coordinate", "northing": "y_coordinate"})
            grid_e = int(df["x_coordinate"].iloc[0] // 100_000)
            grid_n = int(df["y_coordinate"].iloc[0] // 100_000)

            df.to_parquet(TMP_PARQUET, index=False)

            s3_key = f"os_terrain_50/terrain50/grid_e={grid_e}/grid_n={grid_n}/terrain50_{tile}.parquet"
            load_file_to_s3(TMP_PARQUET, S3_INCOMING_BUCKET, s3_key)
            add_glue_partition_en(grid_e, grid_n, "os_terrain_50_terrain50", ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
            print(f"  Tile {tile} (grid_e={grid_e}, grid_n={grid_n}): {len(df):,} points")

    cache_path.unlink()
    print("Done.")


if __name__ == "__main__":
    load()
