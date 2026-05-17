"""
Helpers for fetching and processing ArcGIS FeatureServer polygon datasets.
"""

import tempfile
from typing import Callable

import pandas as pd
import requests
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

_to_osgb = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True).transform

PAGE_SIZE = 2000


def fetch_all_features(url: str, out_fields: str) -> list[dict]:
    """Page through an ArcGIS FeatureServer query endpoint and return all features."""
    features = []
    offset = 0
    while True:
        params = {
            "where": "1=1",
            "outFields": out_fields,
            "returnGeometry": "true",
            "outSR": "4326",
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
            "f": "geojson",
        }
        response = requests.get(url, params=params, timeout=120)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(f"ArcGIS error: {data['error']}")
        page = data.get("features", [])
        features.extend(page)
        print(f"  Fetched {len(features)} features...")
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return features


def geometry_columns(f: dict) -> dict:
    """Return the standard geometry + spatial index columns for a GeoJSON feature."""
    geom_wgs84 = shape(f["geometry"])
    geom_osgb = transform(_to_osgb, geom_wgs84)
    centroid = geom_osgb.centroid
    minx, miny, maxx, maxy = geom_osgb.bounds
    return {
        "geometry_wgs84_wkt": geom_wgs84.wkt,
        "geometry_osgb_wkt": geom_osgb.wkt,
        "centre_e": round(centroid.x),
        "centre_n": round(centroid.y),
        "bbox_min_e": round(minx),
        "bbox_min_n": round(miny),
        "bbox_max_e": round(maxx),
        "bbox_max_n": round(maxy),
    }


def fetch_and_build_dataframe(
    url: str,
    out_fields: str,
    process_feature: Callable[[dict], dict],
    columns: list[str],
) -> pd.DataFrame:
    """Fetch all features, process each with process_feature, return a DataFrame."""
    features = fetch_all_features(url, out_fields)
    print(f"  Total: {len(features)} features")
    print("Processing geometries...")
    rows = [process_feature(f) for f in features if f.get("geometry") is not None]
    skipped = len(features) - len(rows)
    if skipped:
        print(f"  Skipped {skipped} features with null geometry")
    return pd.DataFrame(rows, columns=columns)
