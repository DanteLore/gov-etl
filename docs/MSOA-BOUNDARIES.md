# ONS MSOA Boundaries 2021

Polygon boundaries for all 7,264 Middle Layer Super Output Areas (MSOAs) in England and
Wales, 2021 vintage. MSOAs are the ONS standard small-area geography with ~7,500 residents
each — fine enough for neighbourhood-level analysis, coarse enough to be stable over time.
Includes Rural-Urban Classification (RUC) for each area.

Boundaries use Super Generalised Clipped (BSC) geometry — suitable for spatial filtering,
bbox lookups and display. Not for precise boundary measurements.

## Schema

**Glue table:** `incoming.ons_msoa_boundaries_msoa`
**S3 location:** `s3://dantelore.data.incoming/ons_msoa_boundaries/msoa/msoa_2021.parquet`

| Column | Type | Description |
|---|---|---|
| `msoa21cd` | string | Stable ONS area code (primary key, e.g. `E02003552`) |
| `msoa21nm` | string | Area name in English (e.g. `Newbury 001`) |
| `msoa21nmw` | string | Area name in Welsh (Wales only, null elsewhere) |
| `ruc21cd` | string | Rural-Urban Classification code (e.g. `D1`, `C2`) |
| `ruc21nm` | string | Rural-Urban Classification description (e.g. `Rural village`) |
| `geometry_wgs84_wkt` | string | Polygon in WGS84 (EPSG:4326, lng/lat) as WKT |
| `geometry_osgb_wkt` | string | Polygon in British National Grid (EPSG:27700, metres) as WKT |
| `centre_e` | int | Centroid easting (OSGB metres) |
| `centre_n` | int | Centroid northing (OSGB metres) |
| `bbox_min_e` | int | Bounding rectangle min easting (OSGB metres) |
| `bbox_min_n` | int | Bounding rectangle min northing (OSGB metres) |
| `bbox_max_e` | int | Bounding rectangle max easting (OSGB metres) |
| `bbox_max_n` | int | Bounding rectangle max northing (OSGB metres) |

## Rural-Urban Classification codes

| Code | Description |
|---|---|
| `A1` | Urban major conurbation |
| `B1` | Urban minor conurbation |
| `C1` | Urban city and town |
| `C2` | Urban city and town in a sparse setting |
| `D1` | Rural town and fringe |
| `D2` | Rural town and fringe in a sparse setting |
| `E1` | Rural village and dispersed |
| `E2` | Rural village and dispersed in a sparse setting |

## Common queries

### Look up MSOAs by name

```sql
SELECT msoa21cd, msoa21nm, ruc21nm, centre_e, centre_n
FROM ons_msoa_boundaries_msoa
WHERE msoa21nm LIKE 'Newbury%'
ORDER BY msoa21nm
```

### Find MSOAs within a bounding box

```sql
-- MSOAs whose centroid falls within ~10km of Newbury town centre (448000, 167000)
SELECT msoa21cd, msoa21nm, ruc21nm
FROM ons_msoa_boundaries_msoa
WHERE centre_e BETWEEN 438000 AND 458000
  AND centre_n BETWEEN 157000 AND 177000
ORDER BY msoa21nm
```

### All rural MSOAs in a region

```sql
SELECT msoa21cd, msoa21nm, ruc21cd, ruc21nm
FROM ons_msoa_boundaries_msoa
WHERE ruc21cd LIKE 'D%' OR ruc21cd LIKE 'E%'
ORDER BY msoa21nm
```

### Join to income estimates

```sql
SELECT
    b.msoa21nm,
    b.ruc21nm,
    i.net_annual_income,
    i.net_income_after_housing
FROM ons_msoa_boundaries_msoa b
JOIN ons_msoa_income_income i ON b.msoa21cd = i.msoa21cd
WHERE b.centre_e BETWEEN 430000 AND 470000
  AND b.centre_n BETWEEN 150000 AND 190000
ORDER BY i.net_annual_income DESC
```

## Source and update cadence

**Source:** ONS Open Geography Portal —
[MSOA_2021_EW_BSC_V3_RUC](https://services1.arcgis.com/ESMARspQHYMw9BZ9/ArcGIS/rest/services/MSOA_2021_EW_BSC_V3_RUC/FeatureServer/0)

MSOA boundaries are updated after each Census (2021 vintage current; next revision ~2031).

**Reload:**
```bash
python ons_msoa_boundaries/ons_msoa_boundaries_load.py
```
