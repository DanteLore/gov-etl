"""
Helpers for fetching data from the Nomis API.
"""

import time
from typing import Any

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
