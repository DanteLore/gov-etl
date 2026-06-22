# EA LiDAR 1m Composite DTM

1m-resolution bare-earth Digital Terrain Model (DTM) for England from the Environment
Agency's National LiDAR Programme. Voids are filled. Each point represents the SW corner
of a 1m grid cell. 60x finer resolution than OS Terrain 50, covering England only.

Data is fetched via the EA WCS endpoint in 10km bounding-box chunks and stored under
100km partitions matching the `os_open_uprn` and `os_terrain_50` partition scheme.

**Only areas of interest are loaded** — the full England extent at 1m resolution would
be ~390 GB. Load additional areas by running the loader with a new `--bbox`.

## Currently loaded areas

| Area | Bbox (OSGB36) | Loaded |
|---|---|---|
| West Berkshire | `430000,155000,490000,190000` | Yes |

## Schema

**Glue table:** `incoming.ea_lidar_1m_dtm`
**S3 location:** `s3://dantelore.data.incoming/ea_lidar_1m/dtm/grid_e={e}/grid_n={n}/`

| Column | Type | Description |
|---|---|---|
| `x_coordinate` | int | OSGB36 easting of cell SW corner (metres) |
| `y_coordinate` | int | OSGB36 northing of cell SW corner (metres) |
| `elevation_m` | float | Elevation above sea level (metres, bare earth) |
| `grid_e` | int | **Partition key** — `floor(x_coordinate / 100000)`, 100km easting tile (0–6) |
| `grid_n` | int | **Partition key** — `floor(y_coordinate / 100000)`, 100km northing tile (0–12) |

Always filter on both `grid_e` and `grid_n` to get partition pruning. See the Conventions
section in the README for the full spatial partitioning standard.

## Common queries

### Elevation at a specific OSGB coordinate (exact 1m cell)

```sql
SELECT x_coordinate, y_coordinate, elevation_m
FROM ea_lidar_1m_dtm
WHERE grid_e = 4 AND grid_n = 1
  AND x_coordinate = 453000
  AND y_coordinate = 167000
```

### Elevation range across a neighbourhood

```sql
SELECT
    MIN(elevation_m) AS min_elev,
    MAX(elevation_m) AS max_elev,
    AVG(elevation_m) AS mean_elev
FROM ea_lidar_1m_dtm
WHERE grid_e = 4 AND grid_n = 1
  AND x_coordinate BETWEEN 452000 AND 454000
  AND y_coordinate BETWEEN 166000 AND 168000
```

### Join UPRN addresses to their precise 1m elevation

```sql
SELECT
    u.uprn,
    u.x_coordinate AS uprn_e,
    u.y_coordinate AS uprn_n,
    e.elevation_m
FROM os_open_uprn_uprn u
JOIN ea_lidar_1m_dtm e
    ON  e.grid_e = u.grid_e
    AND e.grid_n = u.grid_n
    AND e.x_coordinate = CAST(u.x_coordinate AS INT)
    AND e.y_coordinate = CAST(u.y_coordinate AS INT)
WHERE u.grid_e = 4 AND u.grid_n = 1
```

### Compare LiDAR elevation to OS Terrain 50 for the same area

```sql
SELECT
    l.x_coordinate,
    l.y_coordinate,
    l.elevation_m AS lidar_1m,
    t.elevation_m AS terrain_50m
FROM ea_lidar_1m_dtm l
JOIN os_terrain_50_terrain50 t
    ON  t.grid_e = l.grid_e
    AND t.grid_n = l.grid_n
    AND t.x_coordinate = (CAST(l.x_coordinate / 50 AS INT) * 50)
    AND t.y_coordinate = (CAST(l.y_coordinate / 50 AS INT) * 50)
WHERE l.grid_e = 4 AND l.grid_n = 1
  AND l.x_coordinate BETWEEN 453000 AND 453100
  AND l.y_coordinate BETWEEN 167000 AND 167100
```

### Flood risk proxy — addresses below a threshold elevation

```sql
SELECT u.uprn, u.x_coordinate, u.y_coordinate, e.elevation_m
FROM os_open_uprn_uprn u
JOIN ea_lidar_1m_dtm e
    ON  e.grid_e = u.grid_e
    AND e.grid_n = u.grid_n
    AND e.x_coordinate = CAST(u.x_coordinate AS INT)
    AND e.y_coordinate = CAST(u.y_coordinate AS INT)
WHERE u.grid_e = 4 AND u.grid_n = 1
  AND e.elevation_m < 50
ORDER BY e.elevation_m
```

## Loading additional areas

The loader fetches data from the EA WCS endpoint by bounding box. To add a new area,
run with a `--bbox` argument (min_e, min_n, max_e, max_n in OSGB36 metres). Chunks
already uploaded are not re-uploaded — the loader will add new partitions alongside
existing ones.

```bash
# Add Thames Valley
python ea_lidar_1m/ea_lidar_1m_load.py --bbox 450000,170000,560000,220000

# Add a single 10km test chunk
python ea_lidar_1m/ea_lidar_1m_load.py --bbox 530000,180000,540000,190000
```

Chunks that fall outside EA coverage (sea, or areas not yet surveyed) are silently
skipped — the WCS returns an exception report which the loader treats as no data.

## Coverage notes

- England only. Scotland and Wales are not covered by the EA LiDAR programme.
- The EA survey is ongoing — some rural areas may have older or lower-quality data.
- 1m resolution means each 10km chunk contains up to 100,000,000 points. Each parquet
  file is typically ~300 MB before compression, ~75 MB after Snappy.
- For areas where 1m precision is not needed, consider using OS Terrain 50 instead —
  its 50m grid covers the whole of GB at a fraction of the storage cost.

## Source and update cadence

**Source:** Environment Agency — [LiDAR Composite DTM 1m](https://environment.data.gov.uk/dataset/13787b9a-26a4-4775-8523-806d13af58fc)
Accessed via WCS endpoint — free, no authentication required.

**WCS base URL:** `https://environment.data.gov.uk/geoservices/datasets/13787b9a-26a4-4775-8523-806d13af58fc/wcs`

**Licence:** Open Government Licence (OGL v3)

The EA update the composite periodically as new survey flights are completed. To refresh
a previously loaded area, re-run the loader with the same bbox — existing S3 files will
be overwritten.
