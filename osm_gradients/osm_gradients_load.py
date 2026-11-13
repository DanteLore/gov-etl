"""
Work out the gradient of every OpenStreetMap road and path where the EA 1m lidar is loaded, from
incoming.osm_paths and incoming.ea_lidar_1m_dtm, and write it to incoming.osm_path_gradients.

For each way: heights every 10 m along it (the median of the 3 x 3 m of lidar around each point, then a 90 m
running median along the way, which removes narrow dips and spikes from unmapped bridges, kerbs, banks and the
few metres OpenStreetMap lines can be off, but leaves steady slopes alone), then the
start and end heights, the climb and descent in the direction the way is drawn, the steepest uphill and downhill
over any 50 m (or the whole way, if shorter), and the 10 m height profile. To get
a route's climb, add up its ways' climb (or descent, for ways it uses backwards).

The lidar is bare earth: bridges are removed, so a way on a bridge would dip to the river or railway below.
Ways tagged bridge=* or tunnel=* get heights interpolated between their ends instead (is_interpolated). What
can't be fixed is flagged in gradient_check (roads steeper than 20%, anything steeper than 40%, heights below
sea level, jumps of over 5 m in 10 m on roads).

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
SMOOTH = 9     # samples in the running median (90 m): removes dips and spikes up to about 40 m wide
ROADS = {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link",
         "tertiary", "tertiary_link", "unclassified", "residential", "living_street", "service", "road"}

SCHEMA = pa.schema([
    ("osm_id", pa.int64()), ("highway", pa.string()), ("name", pa.string()), ("length_m", pa.float64()),
    ("elevation_start_m", pa.float64()), ("elevation_end_m", pa.float64()), ("elevation_min_m", pa.float64()),
    ("elevation_max_m", pa.float64()), ("climb_m", pa.float64()), ("descent_m", pa.float64()),
    ("max_uphill_pct", pa.float64()), ("max_downhill_pct", pa.float64()), ("mean_gradient_pct", pa.float64()),
    ("is_interpolated", pa.bool_()), ("gradient_check", pa.string()), ("elevation_profile_m", pa.list_(pa.float64())),
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


def smooth(heights):
    """Remove narrow dips and spikes (unmapped bridges and culverts, banks beside the line) but keep slopes.

    A running median over SMOOTH samples leaves any steadily rising or falling stretch exactly as it is and
    removes bumps narrower than half the window; near the ends the window shrinks to stay centred. Then the
    last few samples at each end are walked outwards: one that steps more than 3 m, and more than three times
    the typical step before it, from the sample inside it (e.g. a way ending at a bridge abutment, where the lidar
    drops to the road below) is replaced by continuing the trend.
    """
    n = len(heights)
    if n < 3:
        return heights
    half = SMOOTH // 2
    out = heights.copy()
    for i in range(1, n - 1):
        width = min(i, n - 1 - i, half)
        out[i] = np.median(heights[i - width:i + width + 1])
    for seq in (out, out[::-1]):  # the tail, then the head (a reversed view writes through to out)
        k = min(half, n - 3)
        base = seq[max(n - k - 5, 0):n - k]
        if len(base) < 2:
            continue
        steps = np.diff(base)
        trend, typical = float(np.median(steps)), float(np.median(np.abs(steps)))
        for j in range(n - k, n):
            step = abs(seq[j] - seq[j - 1])
            if step > 3 and step > 3 * max(typical, 0.1):
                seq[j] = seq[j - 1] + trend
    return out


def check(highway, heights, window):
    """Why the gradients may be wrong, or None. Kept as a flag rather than corrected: these are usually ground
    the lidar sees differently from the way (an unmapped bridge, a way drawn on a cutting slope, ground dug out
    or built up since the survey) and can't be fixed from the lidar alone."""
    steepest = float(np.max(np.abs(window))) if len(window) else 0.0
    reasons = []
    if heights.min() < 0:
        reasons.append("below sea level")
    if highway in ROADS and steepest > 20:
        reasons.append("road steeper than 20%")
    elif steepest > 40:
        reasons.append("steeper than 40%")
    if highway in ROADS and len(heights) > 1 and np.abs(np.diff(heights)).max() > 5:
        reasons.append("jump of over 5 m in 10 m")
    return ", ".join(reasons) or None


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
    heights = smooth(heights)
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
        "is_interpolated": interpolated, "gradient_check": check(row["highway"], heights, window),
        "elevation_profile_m": [round(h, 2) for h in heights],
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
