"""
Test cycle routes from the North East Thatcham (SP14) allocation to Thatcham station, Kennet School and the town
centre on the OpenStreetMap network, and find where Thatcham's cycle paths stop. Writes three tables:

- incoming.osm_cycle_routes: one row per origin, destination and route type, with length, climb (and descent,
  which is the climb on the way back), how much is on each kind of cycle provision, main roads crossed without a
  mapped crossing, and the longest stretch without low-stress provision
- incoming.osm_cycle_route_segments: the ways each route uses, in order
- incoming.osm_cycle_network_ends: places where a cycleway or shared path stops at a main road, a footway or
  nothing, across the Thatcham area

Origins are points every 250 m across the SP14 boundary (sp14_boundary.geojson), each joined to the nearest
point of today's network; the site is mostly fields, so `snap_m` says how far that is. Three route types:

- shortest: the shortest route a bike may legally use (no motorways, footways without cycle permission, steps)
- low_stress_preferred: as above, but main roads cost four times their length and painted lanes 1.6 times, so
  the route takes paths and quiet streets where they exist
- low_stress_only: only cycleways, shared paths, cycle tracks and quiet streets; `found` is false if there is
  no such route

Built from incoming.osm_paths, osm_points and osm_path_gradients (for climb). Rerun after reloading those.

Usage:
    python osm_cycle_routes/osm_cycle_routes_load.py
"""

import heapq
import json
import math
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import boto3
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.aws import load_file_to_s3

S3_INCOMING_BUCKET = "dantelore.data.incoming"
# The Thatcham area: Newbury's eastern edge to Midgham, Cold Ash to Crookham Common
AREA = {"min_lon": -1.32, "max_lon": -1.18, "min_lat": 51.38, "max_lat": 51.43}
GRID = (4, 1)
ORIGIN_SPACING_M = 250
DESTINATIONS = {
    # NaPTAN 9100THATCHM
    "Thatcham station": (-1.24319, 51.39384),
    # School URN 110055, location from the PCT
    "Kennet School": (-1.24868, 51.40174),
    # NaPTAN 030055890001/2, the Thatcham Broadway bus stops
    "Town centre (Broadway)": (-1.25749, 51.40308),
}
MAIN_ROADS = {"trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link", "tertiary", "tertiary_link"}
QUIET_ROADS = {"residential", "living_street", "service", "unclassified", "road"}
PATHS = {"cycleway", "path", "footway", "bridleway", "pedestrian", "track"}
LOW_STRESS = {"cycleway", "shared_path", "cycle_track", "quiet_road"}
COST = {"cycleway": 1.0, "cycle_track": 1.0, "shared_path": 1.05, "quiet_road": 1.15, "track": 1.3,
        "path_unclear": 1.3, "cycle_lane": 1.6, "main_road": 4.0}
YES = {"yes", "designated", "permissive"}

TO_OSGB = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
s3 = boto3.client("s3")


def provision(w):
    """How a way serves cycling, or None if a bike may not use it."""
    hw, bicycle, access = w["highway"], w["bicycle"], w["access"]
    if bicycle in ("no", "dismount", "use_sidepath") or hw in ("motorway", "motorway_link", "steps", "construction",
                                                                "proposed", "bus_guideway", "raceway"):
        return None
    if access in ("no", "private") and bicycle not in YES:
        return None
    lanes = {w["cycleway"], w["cycleway_left"], w["cycleway_right"], w["cycleway_both"]}
    if hw == "cycleway":
        return "cycleway" if w["segregated"] == "yes" or w["foot"] not in YES else "shared_path"
    if hw in ("footway", "pedestrian"):
        if bicycle not in YES:
            return None  # cycling on a footway is not allowed unless it is signed for bikes
        return "cycleway" if w["segregated"] == "yes" else "shared_path"
    if hw in ("path", "bridleway"):
        if bicycle in YES or hw == "bridleway":
            return "cycleway" if w["segregated"] == "yes" else "shared_path"
        return "path_unclear"  # a path with no cycling tag: often a public footpath
    if hw == "track":
        return "track"
    if lanes & {"track", "separate"}:
        return "cycle_track"
    if hw in MAIN_ROADS:
        return "cycle_lane" if lanes & {"lane", "share_busway"} else "main_road"
    if hw in QUIET_ROADS:
        return "quiet_road"
    return None


def metres(a, b):
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[0] - a[0]) / 2) ** 2
    return 2 * 6_371_008.8 * math.asin(math.sqrt(h))


def read_grid(prefix, columns, tmp):
    key = next(o["Key"] for o in s3.list_objects_v2(Bucket=S3_INCOMING_BUCKET,
                                                    Prefix=f"{prefix}grid_e={GRID[0]}/grid_n={GRID[1]}/")["Contents"])
    path = Path(tmp) / Path(key).name
    s3.download_file(S3_INCOMING_BUCKET, key, str(path))
    return pq.read_table(path, columns=columns)


def in_area(t, lon="min_lon", lat="min_lat", lon2="max_lon", lat2="max_lat"):
    return t.filter(pc.and_(pc.and_(pc.greater_equal(t[lon2], AREA["min_lon"]), pc.less_equal(t[lon], AREA["max_lon"])),
                            pc.and_(pc.greater_equal(t[lat2], AREA["min_lat"]), pc.less_equal(t[lat], AREA["max_lat"]))))


class Network:
    def __init__(self, tmp):
        cols = ["osm_id", "highway", "name", "ref", "cycleway", "cycleway_left", "cycleway_right", "cycleway_both",
                "bicycle", "foot", "segregated", "access", "oneway", "oneway_bicycle", "maxspeed", "node_ids",
                "min_lon", "min_lat", "max_lon", "max_lat", "geometry_wkt"]
        ways = in_area(read_grid("osm/paths/", cols, tmp)).to_pylist()
        try:
            grads = read_grid("osm_path_gradients/", ["osm_id", "length_m", "elevation_profile_m",
                                                      "max_uphill_pct", "max_downhill_pct"], tmp).to_pylist()
            self.profiles = {g["osm_id"]: g for g in grads}
        except (StopIteration, KeyError):
            self.profiles = {}
        points = read_grid("osm/points/", ["osm_id", "osm_type", "feature", "crossing", "highway", "lon", "lat"], tmp)
        self.crossings = {p["osm_id"]: p for p in points.to_pylist()
                          if p["osm_type"] == "node" and p["feature"] in ("crossing", "traffic_signals")}
        self.coords, self.ways, self.edges = {}, {}, defaultdict(list)
        self.main_road_nodes = set()
        self.node_ways = defaultdict(set)
        for w in ways:
            kind = provision(w)
            coords = [tuple(map(float, p.split())) for p in w["geometry_wkt"][11:-1].split(", ")]
            nodes = w["node_ids"]
            if len(coords) != len(nodes):
                continue
            w["provision"] = kind
            self.ways[w["osm_id"]] = w
            for n, c in zip(nodes, coords):
                self.coords[n] = c
                self.node_ways[n].add(w["osm_id"])
                if w["highway"] in MAIN_ROADS:
                    self.main_road_nodes.add(n)
            if kind is None:
                continue
            dist = np.concatenate([[0.0], np.cumsum([metres(a, b) for a, b in zip(coords, coords[1:])])])
            heights = self.heights(w["osm_id"], dist)
            forward_only = w["oneway"] in ("yes", "1", "true") and w["oneway_bicycle"] != "no" and w["highway"] not in PATHS
            backward_only = w["oneway"] == "-1" and w["oneway_bicycle"] != "no"
            for i in range(len(nodes) - 1):
                length = dist[i + 1] - dist[i]
                rise = 0.0 if heights is None else heights[i + 1] - heights[i]
                if not backward_only:
                    self.edges[nodes[i]].append((nodes[i + 1], length, rise, w["osm_id"], kind))
                if not forward_only:
                    self.edges[nodes[i + 1]].append((nodes[i], length, -rise, w["osm_id"], kind))
        print(f"  network: {len(self.ways):,} ways, {len(self.edges):,} routable nodes, "
              f"gradients for {sum(1 for w in self.ways if w in self.profiles):,} ways")

    def heights(self, osm_id, dist):
        g = self.profiles.get(osm_id)
        if not g or not g["elevation_profile_m"]:
            return None
        profile = np.array(g["elevation_profile_m"])
        at = np.minimum(np.arange(len(profile)) * 10.0, g["length_m"])
        at[-1] = g["length_m"]
        return np.interp(dist, at, profile)

    def nearest(self, lon, lat, allowed=None):
        best, best_d = None, math.inf
        for n in self.edges:
            if allowed and not any(e[4] in allowed for e in self.edges[n]):
                continue
            c = self.coords[n]
            d = metres((lon, lat), c)
            if d < best_d:
                best, best_d = n, d
        return best, best_d

    def route(self, start, end, route_type):
        """Dijkstra; returns the list of edges (from, to, length, rise, osm_id, kind) or None."""
        dist, prev, heap = {start: 0.0}, {}, [(0.0, start)]
        while heap:
            d, n = heapq.heappop(heap)
            if n == end:
                break
            if d > dist[n]:
                continue
            for m, length, rise, osm_id, kind in self.edges[n]:
                if route_type == "low_stress_only" and kind not in LOW_STRESS:
                    continue
                cost = length * (COST[kind] if route_type != "shortest" else 1.0)
                if d + cost < dist.get(m, math.inf):
                    dist[m], prev[m] = d + cost, (n, length, rise, osm_id, kind)
                    heapq.heappush(heap, (d + cost, m))
        if end not in prev and end != start:
            return None
        path, n = [], end
        while n != start:
            p, length, rise, osm_id, kind = prev[n]
            path.append((p, n, length, rise, osm_id, kind))
            n = p
        return path[::-1]


def origins():
    gj = json.load(open(Path(__file__).parent / "sp14_boundary.geojson"))
    outer, *holes = gj["geometry"]["coordinates"]
    to_osgb = lambda ring: np.array(TO_OSGB.transform([p[0] for p in ring], [p[1] for p in ring])).T
    outer_xy, holes_xy = to_osgb(outer), [to_osgb(h) for h in holes]

    def inside(x, y, ring):
        xs, ys, hit = ring[:, 0], ring[:, 1], False
        for i in range(len(ring) - 1):
            if (ys[i] > y) != (ys[i + 1] > y) and x < xs[i] + (y - ys[i]) * (xs[i + 1] - xs[i]) / (ys[i + 1] - ys[i]):
                hit = not hit
        return hit

    (x0, y0), (x1, y1) = outer_xy.min(axis=0), outer_xy.max(axis=0)
    pts = [(x, y) for x in np.arange(x0 + ORIGIN_SPACING_M / 2, x1, ORIGIN_SPACING_M)
           for y in np.arange(y0 + ORIGIN_SPACING_M / 2, y1, ORIGIN_SPACING_M)
           if inside(x, y, outer_xy) and not any(inside(x, y, h) for h in holes_xy)]
    back = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
    return [back.transform(x, y) for x, y in pts]


def summarise(net, path, keys):
    """A route's summary row and its segment rows."""
    length = sum(e[2] for e in path)
    by_kind = defaultdict(float)
    for e in path:
        by_kind[e[5]] += e[2]
    climb = sum(e[3] for e in path if e[3] > 0)
    descent = -sum(e[3] for e in path if e[3] < 0)
    # Steepest bit: each way's steepest 50 m in the direction travelled
    steepest = 0.0
    segments = []
    for e in path:
        if segments and segments[-1]["osm_id"] == e[4]:
            s = segments[-1]
            s["length_m"] += e[2]
            s["climb_m"] += max(e[3], 0)
            s["descent_m"] += max(-e[3], 0)
            s["coords"].append(net.coords[e[1]])
        else:
            w = net.ways[e[4]]
            segments.append({**keys, "seq": len(segments) + 1, "osm_id": e[4], "name": w["name"] or w["ref"],
                             "highway": w["highway"], "provision": e[5], "maxspeed": w["maxspeed"],
                             "length_m": e[2], "climb_m": max(e[3], 0), "descent_m": max(-e[3], 0),
                             "forward": w["node_ids"].index(e[1]) > w["node_ids"].index(e[0]),
                             "coords": [net.coords[e[0]], net.coords[e[1]]]})
    for s in segments:
        g = net.profiles.get(s["osm_id"])
        if g and s["length_m"] >= 30:
            steepest = max(steepest, g["max_uphill_pct"] if s["forward"] else g["max_downhill_pct"])
    # Main roads crossed (not ridden along): a node on a main road where the route arrives and leaves on other ways
    crossings, unmarked = 0, []
    for a, b in zip(path, path[1:]):
        node = a[1]
        if node in net.main_road_nodes and a[5] != "main_road" and b[5] != "main_road" \
                and net.ways[a[4]]["highway"] not in MAIN_ROADS and net.ways[b[4]]["highway"] not in MAIN_ROADS:
            crossings += 1
            c = net.crossings.get(node)
            if not c or c["crossing"] in (None, "unmarked", "no", "informal"):
                road = next((net.ways[w]["name"] or net.ways[w]["ref"] for w in net.node_ways[node]
                             if net.ways[w]["highway"] in MAIN_ROADS), None)
                unmarked.append(road or "unnamed road")
    # Stretches without low-stress provision
    gaps, run, names = [], 0.0, []
    for s in segments + [None]:
        if s and s["provision"] not in LOW_STRESS:
            run += s["length_m"]
            names.append(s["name"] or s["highway"])
        elif run:
            gaps.append((run, names))
            run, names = 0.0, []
    longest = max(gaps, default=(0.0, []))
    coords = [net.coords[path[0][0]]] + [net.coords[e[1]] for e in path]
    for s in segments:
        s["geometry_wkt"] = "LINESTRING(" + ", ".join(f"{x:.6f} {y:.6f}" for x, y in s.pop("coords")) + ")"
        s.pop("forward")
        for k in ("length_m", "climb_m", "descent_m"):
            s[k] = round(s[k], 1)
    summary = {**keys, "found": True, "length_m": round(length, 1), "climb_m": round(climb, 1),
               "descent_m": round(descent, 1), "max_uphill_pct": round(steepest, 1),
               "low_stress_pct": round(100 * sum(v for k, v in by_kind.items() if k in LOW_STRESS) / length, 1) if length else None,
               **{f"{k}_m": round(by_kind.get(k, 0.0), 1) for k in COST},
               "main_roads_crossed": crossings, "unmarked_crossings": len(unmarked),
               "unmarked_crossing_roads": ", ".join(dict.fromkeys(unmarked)) or None,
               "longest_gap_m": round(longest[0], 1),
               "longest_gap_ways": ", ".join(dict.fromkeys(n for n in longest[1] if n)) or None,
               "geometry_wkt": "LINESTRING(" + ", ".join(f"{x:.6f} {y:.6f}" for x, y in coords) + ")"}
    return summary, segments


def network_ends(net):
    """Where a cycleway, shared path or cycle track ends without carrying on along another one or a quiet street."""
    infra = {"cycleway", "shared_path", "cycle_track"}
    rows = []
    for w in net.ways.values():
        if w["provision"] not in infra:
            continue
        for n in {w["node_ids"][0], w["node_ids"][-1]}:
            others = [net.ways[x] for x in net.node_ways[n] if x != w["osm_id"]]
            kinds = {o["provision"] for o in others}
            if kinds & (infra | {"quiet_road"}):
                continue  # the route carries on
            if kinds & {"main_road", "cycle_lane"}:
                ends_at = "main road"
            elif kinds & {"track", "path_unclear"}:
                ends_at = "track or unclear path"
            elif others:
                ends_at = "footway or way without cycle access"
            else:
                ends_at = "dead end"
            c = net.crossings.get(n)
            meets = next((o["name"] or o["ref"] for o in others if o["name"] or o["ref"]), None)
            rows.append({"node_id": n, "lon": net.coords[n][0], "lat": net.coords[n][1], "ends_at": ends_at,
                         "path_osm_id": w["osm_id"], "path_name": w["name"], "path_provision": w["provision"],
                         "meets_name": meets, "meets_highway": next((o["highway"] for o in others), None),
                         "crossing": (c["crossing"] or c["feature"]) if c else None})
    return rows


def write(rows, table):
    with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
        pq.write_table(pa.Table.from_pylist(rows), tmp.name, compression="zstd")
        load_file_to_s3(tmp.name, S3_INCOMING_BUCKET, f"{table}/{table}.parquet")
    print(f"  {table}: {len(rows):,} rows")


def load():
    with tempfile.TemporaryDirectory() as tmp:
        net = Network(tmp)
    routes, segments = [], []
    starts = origins()
    print(f"  {len(starts)} origins across the SP14 site")
    for i, (lon, lat) in enumerate(starts, 1):
        start, snap = net.nearest(lon, lat)
        start_low, snap_low = net.nearest(lon, lat, LOW_STRESS)
        for dest, (dlon, dlat) in DESTINATIONS.items():
            end, _ = net.nearest(dlon, dlat)
            end_low, _ = net.nearest(dlon, dlat, LOW_STRESS)
            for route_type in ("shortest", "low_stress_preferred", "low_stress_only"):
                s, e, snapped = (start_low, end_low, snap_low) if route_type == "low_stress_only" else (start, end, snap)
                keys = {"origin_id": i, "origin_lon": round(lon, 6), "origin_lat": round(lat, 6),
                        "snap_m": round(snapped, 1), "destination": dest, "route_type": route_type}
                path = net.route(s, e, route_type)
                if not path:
                    routes.append({**keys, "found": False})
                    continue
                summary, segs = summarise(net, path, keys)
                routes.append(summary)
                segments.extend(segs)
    columns = list(max(routes, key=len).keys())
    write([{c: r.get(c) for c in columns} for r in routes], "osm_cycle_routes")
    write(segments, "osm_cycle_route_segments")
    write(network_ends(net), "osm_cycle_network_ends")


if __name__ == "__main__":
    load()
