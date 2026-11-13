"""
Load the OpenStreetMap road and path network for England into S3, for testing walking and cycling routes:
every way tagged highway=* (roads, cycleways, footways, bridleways, paths, tracks...) with its cycling and
walking tags, node IDs (to build a routable network) and geometry, plus point features that matter on a route:
crossings, signals, barriers, level crossings, cycle parking and schools.

- incoming.osm_paths: one row per way
- incoming.osm_points: one row per node, or per area (cycle parking, schools) at its centre

Source: Geofabrik's daily England extract (england-latest.osm.pbf, about 1.7 GB). Both tables are replaced on
each load. Partitioned by 100 km OSGB grid square (grid_e, grid_n) of the way's first node / the point.
OpenStreetMap data is © OpenStreetMap contributors, ODbL 1.0.

Usage:
    python osm/osm_load.py
    python osm/osm_load.py --pbf /path/to/england-latest.osm.pbf   # reuse a downloaded extract
"""

import argparse
import json
import math
import sys
import tempfile
from datetime import date
from pathlib import Path

import boto3
import osmium
import pyarrow as pa
import pyarrow.parquet as pq
import requests
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3, add_glue_partition_en

S3_INCOMING_BUCKET = "dantelore.data.incoming"
ATHENA_DATABASE = "incoming"
ATHENA_RESULTS_BUCKET = "dantelore.queryresults"
PBF_URL = "https://download.geofabrik.de/europe/united-kingdom/england-latest.osm.pbf"
BATCH = 100_000

PATH_TAGS = ["highway", "name", "ref", "cycleway", "cycleway:left", "cycleway:right", "cycleway:both", "bicycle",
             "foot", "segregated", "surface", "smoothness", "lit", "maxspeed", "oneway", "oneway:bicycle", "access",
             "motor_vehicle", "width", "incline", "bridge", "tunnel", "layer", "sidewalk", "junction", "area"]
POINT_TAGS = ["highway", "crossing", "crossing_ref", "barrier", "railway", "amenity", "bicycle", "foot", "kerb",
              "capacity", "covered", "bicycle_parking", "name"]
POINT_HIGHWAYS = {"crossing", "traffic_signals", "give_way", "stop", "mini_roundabout"}
POINT_AMENITIES = {"bicycle_parking", "bicycle_rental", "bicycle_repair_station", "school", "college"}


def column(tag):
    return tag.replace(":", "_")


PATH_SCHEMA = pa.schema(
    [("osm_id", pa.int64())] + [(column(t), pa.string()) for t in PATH_TAGS]
    + [("tags_json", pa.string()), ("node_ids", pa.list_(pa.int64())), ("length_m", pa.float64()),
       ("start_lon", pa.float64()), ("start_lat", pa.float64()), ("end_lon", pa.float64()), ("end_lat", pa.float64()),
       ("min_lon", pa.float64()), ("min_lat", pa.float64()), ("max_lon", pa.float64()), ("max_lat", pa.float64()),
       ("geometry_wkt", pa.string()), ("snapshot_date", pa.string())])
POINT_SCHEMA = pa.schema(
    [("osm_id", pa.int64()), ("osm_type", pa.string()), ("feature", pa.string())]
    + [(column(t), pa.string()) for t in POINT_TAGS]
    + [("tags_json", pa.string()), ("lon", pa.float64()), ("lat", pa.float64()), ("snapshot_date", pa.string())])

TO_OSGB = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)


def metres(lon1, lat1, lon2, lat2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6_371_008.8 * math.asin(math.sqrt(a))


def point_feature(tags):
    """What makes a tagged node worth keeping, or None."""
    if tags.get("highway") in POINT_HIGHWAYS:
        return tags["highway"]
    if "crossing" in tags:
        return "crossing"
    if tags.get("railway") in ("level_crossing", "crossing"):
        return "level_crossing"
    if "barrier" in tags:
        return "barrier"
    if tags.get("amenity") in POINT_AMENITIES:
        return tags["amenity"]
    return None


class TileWriter:
    """Buffers rows and writes them to one parquet file per 100 km grid square."""

    def __init__(self, name, schema, tmp):
        self.name, self.schema, self.tmp = name, schema, Path(tmp)
        self.rows, self.writers, self.counts = [], {}, {}

    def add(self, row, lon, lat):
        self.rows.append((row, lon, lat))
        if len(self.rows) >= BATCH:
            self.flush()

    def flush(self):
        if not self.rows:
            return
        xs, ys = TO_OSGB.transform([r[1] for r in self.rows], [r[2] for r in self.rows])
        tiles = {}
        for (row, _, _), x, y in zip(self.rows, xs, ys):
            if math.isfinite(x) and math.isfinite(y):
                tiles.setdefault((int(x // 100_000), int(y // 100_000)), []).append(row)
        for tile, rows in tiles.items():
            if tile not in self.writers:
                path = self.tmp / f"{self.name}_{tile[0]}_{tile[1]}.parquet"
                self.writers[tile] = pq.ParquetWriter(path, self.schema, compression="zstd")
            self.writers[tile].write_table(pa.Table.from_pylist(rows, schema=self.schema))
            self.counts[tile] = self.counts.get(tile, 0) + len(rows)
        self.rows = []

    def close(self):
        self.flush()
        for w in self.writers.values():
            w.close()


def read_pbf(pbf, tmp, snapshot):
    paths, points = TileWriter("osm_paths", PATH_SCHEMA, tmp), TileWriter("osm_points", POINT_SCHEMA, tmp)
    fp = (osmium.FileProcessor(str(pbf)).with_locations()
          .with_filter(osmium.filter.KeyFilter("highway", "crossing", "railway", "barrier", "amenity")))
    for obj in fp:
        tags = dict(obj.tags)
        if obj.is_node():
            feature = point_feature(tags)
            if feature:
                loc = obj.location
                points.add({"osm_id": obj.id, "osm_type": "node", "feature": feature,
                            **{column(t): tags.get(t) for t in POINT_TAGS}, "tags_json": json.dumps(tags),
                            "lon": loc.lon, "lat": loc.lat, "snapshot_date": snapshot}, loc.lon, loc.lat)
        elif obj.is_way():
            coords = [(n.lon, n.lat) for n in obj.nodes if n.location.valid()]
            if not coords:
                continue
            if "highway" in tags:
                lons, lats = [c[0] for c in coords], [c[1] for c in coords]
                paths.add({"osm_id": obj.id, **{column(t): tags.get(t) for t in PATH_TAGS},
                           "tags_json": json.dumps(tags), "node_ids": [n.ref for n in obj.nodes],
                           "length_m": sum(metres(*a, *b) for a, b in zip(coords, coords[1:])),
                           "start_lon": lons[0], "start_lat": lats[0], "end_lon": lons[-1], "end_lat": lats[-1],
                           "min_lon": min(lons), "min_lat": min(lats), "max_lon": max(lons), "max_lat": max(lats),
                           "geometry_wkt": "LINESTRING(" + ", ".join(f"{x:.7f} {y:.7f}" for x, y in coords) + ")",
                           "snapshot_date": snapshot}, lons[0], lats[0])
            elif tags.get("amenity") in POINT_AMENITIES:
                # Areas (cycle shelters, school grounds): the mean of the outline's nodes
                lon, lat = sum(c[0] for c in coords) / len(coords), sum(c[1] for c in coords) / len(coords)
                points.add({"osm_id": obj.id, "osm_type": "way", "feature": tags["amenity"],
                            **{column(t): tags.get(t) for t in POINT_TAGS}, "tags_json": json.dumps(tags),
                            "lon": lon, "lat": lat, "snapshot_date": snapshot}, lon, lat)
    paths.close()
    points.close()
    return paths, points


def replace_table(writer):
    """Upload each tile, after deleting the previous load's files (tiles can disappear between loads)."""
    s3 = boto3.client("s3")
    prefix = f"osm/{writer.name.removeprefix('osm_')}/"
    old = [o["Key"] for page in s3.get_paginator("list_objects_v2").paginate(Bucket=S3_INCOMING_BUCKET, Prefix=prefix)
           for o in page.get("Contents", [])]
    for i in range(0, len(old), 1000):
        s3.delete_objects(Bucket=S3_INCOMING_BUCKET, Delete={"Objects": [{"Key": k} for k in old[i:i + 1000]]})
    for (e, n), count in sorted(writer.counts.items()):
        load_file_to_s3(str(writer.tmp / f"{writer.name}_{e}_{n}.parquet"), S3_INCOMING_BUCKET,
                        f"{prefix}grid_e={e}/grid_n={n}/{writer.name}_{e}_{n}.parquet")
        add_glue_partition_en(e, n, writer.name, ATHENA_DATABASE, ATHENA_RESULTS_BUCKET)
    print(f"  {writer.name}: {sum(writer.counts.values()):,} rows in {len(writer.counts)} grid squares")


def load(pbf=None):
    with tempfile.TemporaryDirectory() as tmp:
        if pbf is None:
            pbf = Path(tmp) / "england-latest.osm.pbf"
            with requests.get(PBF_URL, stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(pbf, "wb") as f:
                    for chunk in r.iter_content(16 << 20):
                        f.write(chunk)
        header = osmium.io.Reader(str(pbf), osmium.osm.osm_entity_bits.NOTHING).header()
        stamp = header.get("osmosis_replication_timestamp")
        snapshot = stamp[:10] if stamp else date.today().isoformat()
        print(f"Reading {pbf} (data as of {snapshot})...")
        paths, points = read_pbf(pbf, tmp, snapshot)
        replace_table(paths)
        replace_table(points)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbf", type=Path, help="An already downloaded England extract")
    args = parser.parse_args()
    load(args.pbf)
