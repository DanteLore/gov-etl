# OS Terrain 50

50m-resolution Digital Terrain Model (DTM) covering all of Great Britain, from Ordnance
Survey's Terrain 50 product. Each point represents the SW corner of a 50m grid cell in
OSGB36 coordinates. ~2,858 10km tiles covering the full GB extent.

## Schema

**Glue table:** `incoming.os_terrain_50_terrain50`
**S3 location:** `s3://dantelore.data.incoming/os_terrain_50/terrain50/grid_e={e}/grid_n={n}/`

| Column | Type | Description |
|---|---|---|
| `x_coordinate` | int | OSGB36 easting of cell SW corner (metres) |
| `y_coordinate` | int | OSGB36 northing of cell SW corner (metres) |
| `elevation_m` | float | Elevation above sea level (metres) |
| `grid_e` | int | **Partition key** — `floor(x_coordinate / 100000)`, 100km easting tile (0–6) |
| `grid_n` | int | **Partition key** — `floor(y_coordinate / 100000)`, 100km northing tile (0–12) |

Always filter on both `grid_e` and `grid_n` to get partition pruning. See the Conventions
section in the README for the full spatial partitioning standard.

## Common queries

### Elevation at a specific OSGB coordinate (nearest 50m cell)

```sql
SELECT x_coordinate, y_coordinate, elevation_m
FROM os_terrain_50_terrain50
WHERE grid_e = 5 AND grid_n = 1
  AND x_coordinate = (CAST(530123 / 50 AS INT) * 50)
  AND y_coordinate = (CAST(180456 / 50 AS INT) * 50)
```

### Average elevation across a 10km tile

```sql
SELECT
    AVG(elevation_m) AS mean_elevation,
    MIN(elevation_m) AS min_elevation,
    MAX(elevation_m) AS max_elevation
FROM os_terrain_50_terrain50
WHERE grid_e = 4 AND grid_n = 1
  AND x_coordinate BETWEEN 430000 AND 440000
  AND y_coordinate BETWEEN 155000 AND 165000
```

### Join UPRN addresses to their nearest elevation

```sql
SELECT
    u.uprn,
    u.x_coordinate AS uprn_e,
    u.y_coordinate AS uprn_n,
    t.elevation_m
FROM os_open_uprn_uprn u
JOIN os_terrain_50_terrain50 t
    ON  t.grid_e = u.grid_e
    AND t.grid_n = u.grid_n
    AND t.x_coordinate = (CAST(u.x_coordinate / 50 AS INT) * 50)
    AND t.y_coordinate = (CAST(u.y_coordinate / 50 AS INT) * 50)
WHERE u.grid_e = 4 AND u.grid_n = 1
```

### Elevation profile across a bounding box (e.g. West Berkshire)

```sql
SELECT x_coordinate, y_coordinate, elevation_m
FROM os_terrain_50_terrain50
WHERE grid_e IN (4, 5) AND grid_n = 1
  AND x_coordinate BETWEEN 430000 AND 490000
  AND y_coordinate BETWEEN 155000 AND 190000
ORDER BY y_coordinate DESC, x_coordinate
```

### Highest points in a 100km square

```sql
SELECT x_coordinate, y_coordinate, elevation_m
FROM os_terrain_50_terrain50
WHERE grid_e = 4 AND grid_n = 1
ORDER BY elevation_m DESC
LIMIT 10
```

## Coverage notes

- Full Great Britain — England, Scotland, Wales. Does not cover Northern Ireland or the
  Channel Islands.
- 50m resolution means each partition contains up to 2,000 × 2,000 = 4M points (in
  practice fewer due to coastal/island tiles being partially void).
- Void cells (sea, outside OS coverage) are excluded from the Parquet files — nodata
  values are dropped at load time.

## Source and update cadence

**Source:** OS Data Hub — [OS Terrain 50](https://osdatahub.os.uk/downloads/open/Terrain50)
Free download, no API key required.

**Licence:** Open Government Licence (OGL v3)

OS publish Terrain 50 updates periodically (typically annually). To refresh:

1. Delete the cached zip if present: `del %TEMP%\gov_etl_cache\os_terrain_50.zip`
2. Re-run the loader — it will re-download and re-upload all tiles:
```bash
python os_terrain_50/os_terrain_50_load.py
```
