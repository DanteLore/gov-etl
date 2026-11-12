"""
Helpers for fetching data from the Nomis API.
"""

import io
import time
import zipfile
from typing import Any

import pandas as pd
import requests

NOMIS_BASE = "https://www.nomisweb.co.uk/api/v01/dataset"
MAX_RETRIES = 5


def fetch_observations(dataset: str, params: dict[str, Any]) -> list[dict]:
    """Fetch all observations from a Nomis dataset, handling pagination."""
    all_obs = []
    offset = 0
    page_size = 25000

    while True:
        page_params = {**params, "recordoffset": offset, "uid": "0x0"}
        for attempt in range(MAX_RETRIES):
            try:
                r = requests.get(
                    f"{NOMIS_BASE}/{dataset}.data.json",
                    params=page_params,
                    timeout=60,
                )
                r.raise_for_status()
                break
            except requests.HTTPError as e:
                if attempt < MAX_RETRIES - 1 and e.response.status_code in (429, 500, 502, 503, 504):
                    time.sleep(2 ** attempt)
                else:
                    raise

        data = r.json()
        obs = data.get("obs", [])
        all_obs.extend(obs)

        if len(obs) < page_size:
            break
        offset += page_size

    return all_obs


def get_codelist(dataset: str, dimension: str) -> list[dict]:
    """Return all codes for a dimension as list of {value, description}."""
    r = requests.get(
        f"{NOMIS_BASE}/{dataset}/{dimension}.def.sdmx.json",
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    cl = data["structure"]["codelists"]["codelist"]
    if isinstance(cl, list):
        cl = cl[0]
    return [
        {"value": c["value"], "description": c["description"]["value"]}
        for c in cl.get("code", [])
    ]


# Census 2021 topic summaries: the bulk zips cover output areas up to countries; wards only come from the API
CENSUS_BULK_URL = "https://www.nomisweb.co.uk/output/census/2021/census2021-{topic}.zip"
CENSUS_BULK_LEVELS = ["oa", "lsoa", "msoa", "ltla"]


def census_topic_levels(topic: str, dataset: str, dimension: str, columns: list[str]):
    """Yield (geography_level, DataFrame) for a Census 2021 topic summary at output area, LSOA, MSOA, local
    authority and ward level. Each frame has geography_code, geography_name and one int column per category,
    named by `columns` in the source's category order."""
    r = requests.get(CENSUS_BULK_URL.format(topic=topic), timeout=300)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        for level in CENSUS_BULK_LEVELS:
            with zf.open(f"census2021-{topic}-{level}.csv") as f:
                df = pd.read_csv(f)
            if len(df.columns) != len(columns) + 3:
                raise ValueError(f"{topic} {level}: expected {len(columns)} categories, got {list(df.columns[3:])}")
            df.columns = ["date", "geography_name", "geography_code"] + columns
            yield level, _census_frame(df, columns)

    obs = fetch_observations_csv(dataset, {"geography": "TYPE153", "measures": "20100", "date": "2021",
                                           "select": f"geography_code,geography_name,{dimension},obs_value"})
    wards = obs.pivot(index=["GEOGRAPHY_CODE", "GEOGRAPHY_NAME"], columns=dimension.upper(), values="OBS_VALUE")
    if list(wards.columns) != list(range(len(columns))):
        raise ValueError(f"{dataset} wards: unexpected categories {list(wards.columns)}")
    wards.columns = columns
    wards = wards.reset_index().rename(columns={"GEOGRAPHY_CODE": "geography_code", "GEOGRAPHY_NAME": "geography_name"})
    yield "ward", _census_frame(wards, columns)


def _census_frame(df, columns):
    df = df[["geography_code", "geography_name"] + columns].copy()
    for col in columns:
        df[col] = df[col].astype("int32")
    return df


def fetch_observations_csv(dataset: str, params: dict[str, Any]):
    """Fetch a Nomis dataset as CSV, all pages, as one DataFrame."""
    frames, offset, page_size = [], 0, 25000
    while True:
        for attempt in range(MAX_RETRIES):
            try:
                r = requests.get(f"{NOMIS_BASE}/{dataset}.data.csv",
                                 params={**params, "recordoffset": offset, "recordlimit": page_size, "uid": "0x0"},
                                 timeout=120)
                r.raise_for_status()
                break
            except requests.HTTPError as e:
                if attempt < MAX_RETRIES - 1 and e.response.status_code in (429, 500, 502, 503, 504):
                    time.sleep(2 ** attempt)
                else:
                    raise
        page = pd.read_csv(io.StringIO(r.text))
        frames.append(page)
        if len(page) < page_size:
            return pd.concat(frames, ignore_index=True)
        offset += page_size
