# VOA 2026 Compiled Rating List

All non-domestic (commercially rated) properties in England and Wales, from the
Valuation Office Agency 2026 compiled rating list. 2.14 million entries covering
every hereditament (unit of property liable for business rates) — shops, offices,
warehouses, factories, pubs, schools, car parks, advertising hoardings and more.

## Schema

**Glue table:** `incoming.voa_rating_list_entries`
**S3 location:** `s3://dantelore.data.incoming/voa_rating_list/entries/postcode_area={area}/`

| Column | Type | Description |
|---|---|---|
| `uarn` | string | Unique Address Reference Number — VOA's property identifier (alphanumeric) |
| `ba_code` | string | Billing authority (local council) code |
| `ndr_community_code` | string | NDR community code |
| `desc_code` | string | Property type code (see table below) |
| `desc_text` | string | Property type description, e.g. `SHOP AND PREMISES` |
| `assessment_reference` | bigint | Internal VOA assessment reference |
| `full_address` | string | Full address as a single concatenated string |
| `number_or_name` | string | Property number or name |
| `street` | string | Street name |
| `town` | string | Town |
| `postal_district` | string | Postal district (e.g. `CENTRAL LONDON`) |
| `county` | string | County |
| `postcode` | string | Full postcode (e.g. `RG14 5RU`) |
| `effective_date` | string | Date entry became effective (DD-MON-YYYY) |
| `rateable_value` | int | Rateable value in £ |
| `appeal_settlement_code` | string | Appeal status code |
| `ba_reference` | string | Billing authority's own reference for this property |
| `list_alteration_date` | string | Date the list entry was last altered (DD-MON-YYYY) |
| `scat_code` | string | Special Category code — more granular than `desc_code` |
| `sub_street_1` | string | Sub-street address level 1 (e.g. building name) |
| `sub_street_2` | string | Sub-street address level 2 (e.g. floor) |
| `sub_street_3` | string | Sub-street address level 3 (e.g. unit) |
| `case_number` | bigint | Appeal case number if applicable |
| `current_from_date` | string | Date current rateable value took effect (DD-MON-YYYY) |
| `postcode_area` | string | **Partition key** — leading letters of postcode, lowercase (e.g. `rg`, `sw`) |

Note: 1,054 rows have a null postcode; these are stored in the `unknown` partition.

## Partition scheme

The table is partitioned by **postcode area** — the leading letter(s) of the postcode
(e.g. `rg` for RG14, `sw` for SW1A). Always filter on `postcode_area` when querying
a specific region — this avoids a full table scan across all 2.14M rows.

```sql
-- Good — partition filter pushes down to S3
SELECT * FROM voa_rating_list_entries
WHERE postcode_area = 'rg'

-- Bad — scans all partitions
SELECT * FROM voa_rating_list_entries
WHERE postcode LIKE 'RG%'
```

## Common property type codes (`desc_code`)

| Code | Description | Count |
|---|---|---|
| `CS` | Shop and premises | 418,620 |
| `CO` | Offices and premises | 363,710 |
| `IF3` | Workshop and premises | 198,482 |
| `CW` | Warehouse and premises | 127,132 |
| `CW3` | Store and premises | 83,578 |
| `CH1` | Self catering holiday unit | 72,797 |
| `CP1` | Car parking space | 41,745 |
| `CL` | Public house and premises | 38,079 |
| `MT1` | Communication station | 35,075 |
| `CR` | Restaurant and premises | 32,605 |
| `IF` | Factory and premises | 27,078 |
| `CA` | Advertising right | 26,679 |
| `EL` | School and premises | 22,386 |

The `scat_code` column provides further granularity within each type.

## Common queries

### Count commercial properties in a postcode area

```sql
SELECT COUNT(*) AS commercial_count
FROM voa_rating_list_entries
WHERE postcode_area = 'rg'
```

### Count by property type in an area

```sql
SELECT desc_code, desc_text, COUNT(*) AS cnt
FROM voa_rating_list_entries
WHERE postcode_area = 'rg'
GROUP BY desc_code, desc_text
ORDER BY cnt DESC
```

### Find all commercial properties in a specific postcode

```sql
SELECT uarn, desc_text, number_or_name, street, town, postcode, rateable_value
FROM voa_rating_list_entries
WHERE postcode_area = 'rg'
  AND postcode = 'RG14 5RU'
ORDER BY rateable_value DESC
```

### Highest rateable values in an area

```sql
SELECT desc_text, full_address, postcode, rateable_value
FROM voa_rating_list_entries
WHERE postcode_area = 'rg'
ORDER BY rateable_value DESC
LIMIT 20
```

### Filter to specific property types

```sql
-- Shops and restaurants only
SELECT number_or_name, street, town, postcode, rateable_value
FROM voa_rating_list_entries
WHERE postcode_area = 'rg'
  AND desc_code IN ('CS', 'CR')
ORDER BY town, street
```

## Joining to OS Code Point Open (postcode coordinates)

The `incoming.os_code_point_open_codepo` table provides OSGB easting/northing for
every postcode. Join on `postcode` to add coordinates to VOA entries.

VOA postcodes are uppercase with a space (e.g. `RG14 5RU`). Code Point Open postcodes
are the same format, so the join works directly.

```sql
SELECT
    v.uarn,
    v.desc_code,
    v.desc_text,
    v.full_address,
    v.postcode,
    v.rateable_value,
    c.eastings,
    c.northings
FROM voa_rating_list_entries v
JOIN os_code_point_open_codepo c
    ON  c.postcode     = v.postcode
    AND c.postcode_area = v.postcode_area
WHERE v.postcode_area = 'rg'
```

Including `postcode_area` on both sides ensures Athena uses partition pruning on
both tables rather than scanning everything.

## Estimating residential address counts

Every entry in this table is a **non-domestic** (commercial) property. Combined with
OS Open UPRN (all addresses), you can estimate residential counts within an area:

```sql
-- Commercial property count by town
SELECT
    town,
    COUNT(*) AS commercial_count,
    SUM(rateable_value) AS total_rateable_value
FROM voa_rating_list_entries
WHERE postcode_area IN ('rg', 'ox', 'sl')
GROUP BY town
ORDER BY commercial_count DESC
```

## Source and update cadence

**Source:** https://voaratinglists.blob.core.windows.net/html/rlidata.htm

Free to download. Usage subject to VOA terms and conditions (personal/research use permitted).

The VOA publish change updates twice weekly. The loaded baseline is epoch `0001` of the
2026 rating list (effective April 2026). To refresh:

1. Check the download portal for a newer epoch number
2. Update `DOWNLOAD_URL` in [voa_rating_list/voa_rating_list_load.py](voa_rating_list/voa_rating_list_load.py)
3. Delete the cached zip: `del %TEMP%\voa_rating_list_download.zip`
4. Re-run: `python voa_rating_list/voa_rating_list_load.py`
