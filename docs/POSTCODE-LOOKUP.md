# ONS Postcode to MSOA Lookup

Best-fit lookup from every postcode in England and Wales (~2.35 million) to MSOA, Local
Authority District, County/Unitary Authority, Region and Country. 2021 Output Area
geography, 2022 admin boundaries.

This is the key join table for linking postcode-keyed datasets (house prices, VOA rating
list, OS Code Point Open) to MSOA-level income estimates and boundaries.

## Schema

**Glue table:** `incoming.ons_postcode_lookup_lookup`
**S3 location:** `s3://dantelore.data.incoming/ons_postcode_lookup/lookup/postcode_area={area}/`

| Column | Type | Description |
|---|---|---|
| `postcode` | string | Full postcode (e.g. `RG14 5RU`) |
| `msoa21cd` | string | MSOA 2021 code (join to `ons_msoa_boundaries_msoa` / `ons_msoa_income_income`) |
| `msoa21nm` | string | MSOA 2021 name |
| `lad22cd` | string | Local Authority District code (2022) |
| `lad22nm` | string | Local Authority District name |
| `ctyua22cd` | string | County/Unitary Authority code (2022) |
| `ctyua22nm` | string | County/Unitary Authority name |
| `rgn22cd` | string | Region code (2022) |
| `rgn22nm` | string | Region name |
| `ctry22cd` | string | Country code |
| `ctry22nm` | string | Country name (England or Wales) |
| `postcode_area` | string | **Partition key** — leading letters of postcode, lowercase (e.g. `rg`) |

Always filter on `postcode_area` to limit the scan to one partition.

## Common queries

### Look up a single postcode

```sql
SELECT *
FROM ons_postcode_lookup_lookup
WHERE postcode_area = 'rg'
  AND postcode = 'RG14 5RU'
```

### All postcodes in a MSOA

```sql
SELECT postcode
FROM ons_postcode_lookup_lookup
WHERE postcode_area = 'rg'
  AND msoa21cd = 'E02003552'
ORDER BY postcode
```

### Join house prices to MSOA income

```sql
SELECT
    p.postcode,
    p.price,
    p.property_type,
    l.msoa21nm,
    i.net_annual_income,
    i.net_income_after_housing
FROM house_prices_ppd p
JOIN ons_postcode_lookup_lookup l
    ON p.postcode = l.postcode
    AND l.postcode_area = LOWER(REGEXP_EXTRACT(p.postcode, '^([A-Za-z]+)'))
JOIN ons_msoa_income_income i
    ON l.msoa21cd = i.msoa21cd
WHERE p.year = '2023'
  AND p.town_city = 'NEWBURY'
ORDER BY i.net_annual_income DESC
```

### Average house price by MSOA for a region

```sql
SELECT
    l.msoa21nm,
    COUNT(*) AS sales,
    ROUND(AVG(p.price)) AS avg_price,
    i.net_annual_income
FROM house_prices_ppd p
JOIN ons_postcode_lookup_lookup l
    ON p.postcode = l.postcode
    AND l.postcode_area = LOWER(REGEXP_EXTRACT(p.postcode, '^([A-Za-z]+)'))
JOIN ons_msoa_income_income i ON l.msoa21cd = i.msoa21cd
WHERE p.year = '2023'
  AND l.ctyua22nm = 'West Berkshire'
GROUP BY l.msoa21nm, i.net_annual_income
ORDER BY avg_price DESC
```

### Postcode count per MSOA (as a proxy for density)

```sql
SELECT
    msoa21cd, msoa21nm,
    COUNT(*) AS postcode_count
FROM ons_postcode_lookup_lookup
WHERE postcode_area IN ('rg', 'ox')
GROUP BY msoa21cd, msoa21nm
ORDER BY postcode_count DESC
LIMIT 20
```

## Notes

- Coverage is England and Wales only — Scotland and Northern Ireland are not included.
- "Best fit" means the postcode is assigned to the MSOA containing the largest share of
  its unit postcodes. A small number of postcodes straddle MSOA boundaries.
- `ctyua22cd` / `ctyua22nm` use 2022 codes which differ slightly from the `ctyua25cd`
  codes in `ons_ctyua_boundaries_ctyua` (2019 vintage codes). For spatial joins use
  the boundaries table; for name matching they are equivalent.

## Source and update cadence

**Source:** ONS Open Geography Portal —
Postcode to OA (2021) to LSOA to MSOA to LAD to CTYUA to RGN to CTRY Best Fit Lookup in EW

Re-run when ONS publish an updated lookup following postcode or boundary changes.

**Reload:**
```bash
python ons_postcode_lookup/ons_postcode_lookup_load.py
```

Note: the loader fetches ~2.35M records from the ArcGIS API using 20 concurrent workers.
Expect ~5–10 minutes to complete.
