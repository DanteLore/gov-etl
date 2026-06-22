import io
import numpy as np
import pandas as pd

_HEADER_KEYS = {"ncols", "nrows", "xllcorner", "yllcorner", "xllcenter", "yllcenter", "cellsize", "nodata_value"}


def parse_asc(data: bytes) -> pd.DataFrame:
    """Parse an ESRI ASCII grid (.asc) file into a DataFrame of (easting, northing, elevation_m).

    The ASC format has a header of key/value lines followed by rows of space-separated values.
    Header keys: ncols, nrows, xllcorner/xllcenter, yllcorner/yllcenter, cellsize, NODATA_value (optional).
    Coordinates are the SW corner of each cell in OSGB36 (EPSG:27700).
    """
    lines = data.decode("ascii").splitlines()

    header = {}
    data_start = 0
    for i, line in enumerate(lines):
        parts = line.split()
        if len(parts) == 2 and parts[0].lower() in _HEADER_KEYS:
            header[parts[0].lower()] = parts[1]
        else:
            data_start = i
            break

    ncols = int(header["ncols"])
    nrows = int(header["nrows"])
    xll = float(header.get("xllcorner", header.get("xllcenter", 0)))
    yll = float(header.get("yllcorner", header.get("yllcenter", 0)))
    cellsize = float(header["cellsize"])
    nodata = float(header.get("nodata_value", -9999))

    grid = np.loadtxt(lines[data_start:], dtype=np.float32, max_rows=nrows)

    # Row 0 in the grid is the northernmost row
    row_idx, col_idx = np.meshgrid(np.arange(nrows), np.arange(ncols), indexing="ij")
    eastings = (xll + col_idx * cellsize).astype(np.int32).ravel()
    northings = (yll + (nrows - 1 - row_idx) * cellsize).astype(np.int32).ravel()
    elevations = grid.ravel()

    mask = elevations != nodata
    return pd.DataFrame({
        "easting": eastings[mask],
        "northing": northings[mask],
        "elevation_m": elevations[mask].astype(np.float32),
    })
