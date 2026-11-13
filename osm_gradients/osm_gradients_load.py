"""
Work out the gradient of every OpenStreetMap road and path where the EA 1m lidar is loaded, from
incoming.osm_paths and incoming.ea_lidar_1m_dtm, and write it to incoming.osm_path_gradients.

For each way: heights every 10 m along it (the median of the 3 x 3 m of lidar around each point, then a running
median of three points, to smooth out kerbs, banks and the few metres OpenStreetMap lines can be off), then the
start and end heights, the climb and descent in the direction the way is drawn, the steepest uphill and downhill
over any 50 m (or the whole way, if shorter), and the 10 m height profile. To get
a route's climb, add up its ways' climb (or descent, for ways it uses backwards).

The lidar is bare earth: bridges are removed, so a way on a bridge would dip to the river or railway below.
Ways tagged bridge=* or tunnel=* get heights interpolated between their ends instead (is_interpolated).

Partitioned like osm_paths, by the 100 km grid square of each way's first node. Rerun after reloading osm_paths
or loading more lidar; each grid square's file is replaced.

Usage:
    python osm_gradients/osm_gradients_load.py
"""

import math
import re
import sys
import tempfile
from pathlib import Path

import boto3
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition_en

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"
TABLE = "osm_path_gradients"
LIDAR_PREFIX = "ea_lidar_1m/dtm/"
PATHS_PREFIX = "osm/paths/"
TILE = 10_000  # lidar files are 10 km squares
STEP = 10      # metres between height samples
WINDOW = 5     # steps in the steepest-gradient window (50 m)

SCHEMA = pa.schema([
    ("osm_id", pa.int64()), ("highway", pa.string()), ("name", pa.string()), ("length_m", pa.float64()),
    ("elevation_start_m", pa.float64()), ("elevation_end_m", pa.float64()), ("elevation_min_m", pa.float64()),
    ("elevation_max_m", pa.float64()), ("climb_m", pa.float64()), ("descent_m", pa.float64()),
    ("max_uphill_pct", pa.float64()), ("max_downhill_pct", pa.float64()), ("mean_gradient_pct", pa.float64()),
    ("is_interpolated", pa.bool_()), ("elevation_profile_m", pa.list_(pa.float64())),
])
TO_OSGB = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
s3 = boto3.client("s3")


def keys(prefix):
    return [o["Key"] for page in s3.get_paginator("list_objects_v2").paginate(Bucket=S3_INCOMING_BUCKET, Prefix=prefix)
            for o in page.get("Contents", []) if o["Key"].endswith(".parquet")]


class Lidar:
    """The loaded lidar tiles as 10 km height grids, read on demand."""

    def __init__(self, tmp):
        self.tmp, self.grids = Path(tmp), {}
        self.files = {}
        for key in keys(LIDAR_PREFIX):
            m = re.search(r"dtm_e(\d+)_n(\d+)\.parquet$", key)
            self.files[(int(m[1]), int(m[2]))] = key

    def tile(self, x, y):
        """The tile (its south-west corner) holding a point, or None. Tiles were loaded in 10 km steps from
        wherever each load's bounding box started, so they aren't on a fixed 10 km grid."""
        for e, n in self.files:
            if e <= x < e + TILE and n <= y < n + TILE:
                return e, n
        return None

    def covers(self, x, y):
        return self.tile(x, y) is not None

    def grid(self, tile):
        if tile not in self.grids:
            path = self.tmp / "lidar.parquet"
            s3.download_file(S3_INCOMING_BUCKET, self.files[tile], str(path))
            t = pq.read_table(path)
            xs, ys = t["x_coordinate"].to_numpy(), t["y_coordinate"].to_numpy()
            grid = np.full((TILE + 2, TILE + 2), np.nan, dtype=np.float32)
            grid[ys - tile[1], xs - tile[0]] = t["elevation_m"].to_numpy()
            self.grids[tile] = grid
            path.unlink()
            print(f"    lidar tile {tile} loaded")
        return self.grids[tile]

    def height(self, x, y):
        """Median of the 3 x 3 cells around a point, or nan."""
        tile = self.tile(x, y)
        if tile is None:
            return math.nan
        g = self.grid(tile)
        i, j = int(y) - tile[1], int(x) - tile[0]
        block = g[max(i - 1, 0):i + 2, max(j - 1, 0):j + 2]
        return float(np.nanmedian(block)) if np.isfinite(block).any() else math.nan


def samples(xs, ys):
    """Points every STEP metres along a line (and its last point), with their distance along it."""
    pts = [(xs[0], ys[0], 0.0)]
    done, carry = 0.0, 0.0
    for (x1, y1), (x2, y2) in zip(zip(xs, ys), zip(xs[1:], ys[1:])):
        seg = math.hypot(x2 - x1, y2 - y1)
        d = STEP - carry
        while d <= seg:
            pts.append((x1 + (x2 - x1) * d / seg, y1 + (y2 - y1) * d / seg, done + d))
            d += STEP
        carry = seg - (d - STEP)
        done += seg
    if done - pts[-1][2] > 0.5:
        pts.append((xs[-1], ys[-1], done))
    return pts, done


def gradients(row, lidar):
    coords = [tuple(map(float, p.split())) for p in row["geometry_wkt"][11:-1].split(", ")]
    xs, ys = TO_OSGB.transform([c[0] for c in coords], [c[1] for c in coords])
    if not any(lidar.covers(x, y) for x, y in zip(xs, ys)):
        return None
    pts, length = samples(list(xs), list(ys))
    heights = np.array([lidar.height(x, y) for x, y, _ in pts])
    if np.isnan(heights).mean() > 0.2:
        return None  # mostly outside the lidar
    dist = np.array([d for _, _, d in pts])
    ok = ~np.isnan(heights)
    heights = np.interp(dist, dist[ok], heights[ok])
    if len(heights) >= 3:
        heights = np.concatenate([heights[:1], np.median([heights[:-2], heights[1:-1], heights[2:]], axis=0),
                                  heights[-1:]])
    interpolated = bool(row["bridge"] and row["bridge"] != "no") or bool(row["tunnel"] and row["tunnel"] != "no")
    if interpolated and length > 0:
        heights = heights[0] + (heights[-1] - heights[0]) * dist / length
    rises = np.diff(heights)
    if len(heights) > WINDOW:
        window = (heights[WINDOW:] - heights[:-WINDOW]) / (dist[WINDOW:] - dist[:-WINDOW]) * 100
    else:
        window = np.array([(heights[-1] - heights[0]) / length * 100 if length > 0 else 0.0])
    return {
        "osm_id": row["osm_id"], "highway": row["highway"], "name": row["name"], "length_m": row["length_m"],
        "elevation_start_m": round(heights[0], 2), "elevation_end_m": round(heights[-1], 2),
        "elevation_min_m": round(heights.min(), 2), "elevation_max_m": round(heights.max(), 2),
        "climb_m": round(float(rises[rises > 0].sum()), 2), "descent_m": round(float(-rises[rises < 0].sum()) + 0.0, 2),
        "max_uphill_pct": round(max(float(window.max()), 0.0), 2),
        "max_downhill_pct": round(max(float(-window.min()), 0.0), 2),
        "mean_gradient_pct": round((heights[-1] - heights[0]) / length * 100, 2) if length > 0 else 0.0,
        "is_interpolated": interpolated, "elevation_profile_m": [round(h, 2) for h in heights],
    }


def load():
    with tempfile.TemporaryDirectory() as tmp:
        lidar = Lidar(tmp)
        print(f"{len(lidar.files)} lidar tiles loaded in the lake")
        squares = {(t[0] // 100_000, t[1] // 100_000) for t in lidar.files}
        for key in keys(PATHS_PREFIX):
            e, n = map(int, re.search(r"grid_e=(\d+)/grid_n=(\d+)/", key).groups())
            if (e, n) not in squares:
                continue
            path = Path(tmp) / "paths.parquet"
            s3.download_file(S3_INCOMING_BUCKET, key, str(path))
            columns = ["osm_id", "highway", "name", "length_m", "bridge", "tunnel", "geometry_wkt"]
            rows = []
            for batch in pq.ParquetFile(path).iter_batches(columns=columns, batch_size=50_000):
                rows.extend(r for r in (gradients(w, lidar) for w in batch.to_pylist()) if r)
            path.unlink()
            out = Path(tmp) / f"{TABLE}.parquet"
            pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), out, compression="zstd")
            load_file_to_s3(str(out), S3_INCOMING_BUCKET, f"{TABLE}/grid_e={e}/grid_n={n}/{TABLE}_{e}_{n}.parquet")
            add_glue_partition_en(e, n, TABLE, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
            print(f"  grid_e={e} grid_n={n}: {len(rows):,} ways")


if __name__ == "__main__":
    load()
