# gov-etl

ETL pipelines loading UK government datasets into the dantelore S3 data lake
(`dantelore.data.incoming`), queryable via Athena.

## Datasets

### 1. DfT AADF Road Traffic Census (`traffic_census/`)

Annual Average Daily Flow data from the Department for Transport.
~578k count-point-year records from 2000 to present.

**Source:** https://roadtraffic.dft.gov.uk/downloads

**S3 path:** `s3://dantelore.data.incoming/traffic_census/aadf/year={year}/`

**Glue table:** `incoming.traffic_census_aadf`

| Field | Type | Description |
|---|---|---|
| `count_point_id` | int | Unique ID for the traffic count point |
| `direction_of_travel` | string | Direction of flow (e.g. `N`, `S`, `E`, `W`, `Combined`) |
| `region_id` | int | DfT region identifier |
| `region_name` | string | Region name (e.g. `South East`) |
| `local_authority_id` | int | Local authority identifier |
| `local_authority_name` | string | Local authority name |
| `road_name` | string | Road identifier (e.g. `A34`) |
| `road_category` | string | Road category code |
| `road_type` | string | `Major` or `Minor` |
| `start_junction_road_name` | string | Road name at start junction |
| `end_junction_road_name` | string | Road name at end junction |
| `easting` | int | OSGB easting of count point (metres) |
| `northing` | int | OSGB northing of count point (metres) |
| `latitude` | double | WGS84 latitude |
| `longitude` | double | WGS84 longitude |
| `link_length_km` | double | Length of the counted road link (km) |
| `link_length_miles` | double | Length of the counted road link (miles) |
| `pedal_cycles` | int | AADF count — pedal cycles |
| `two_wheeled_motor_vehicles` | int | AADF count — motorcycles/mopeds |
| `cars_and_taxis` | int | AADF count — cars and taxis |
| `buses_and_coaches` | int | AADF count — buses and coaches |
| `lgvs` | int | AADF count — light goods vehicles |
| `hgvs_2_rigid_axle` | int | AADF count — HGVs, 2-axle rigid |
| `hgvs_3_rigid_axle` | int | AADF count — HGVs, 3-axle rigid |
| `hgvs_4_or_more_rigid_axle` | int | AADF count — HGVs, 4+ axle rigid |
| `hgvs_3_or_4_articulated_axle` | int | AADF count — HGVs, 3–4 axle articulated |
| `hgvs_5_articulated_axle` | int | AADF count — HGVs, 5-axle articulated |
| `hgvs_6_articulated_axle` | int | AADF count — HGVs, 6-axle articulated |
| `all_hgvs` | int | AADF count — all HGVs combined |
| `all_motor_vehicles` | int | AADF count — all motor vehicles combined |
| `year` | string | **Partition key** — census year (e.g. `2023`) |

**Load all years:**
```bash
python traffic_census/traffic_census_bulk_load.py
```

**Load a specific year:**
```bash
python traffic_census/traffic_census_bulk_load.py --year 2024
```

**When to re-run:** The DfT typically publishes updated data annually (around June).
Re-run with `--year <new_year>` when new data is released.

---

### 2. Land Registry Price Paid Data (`house_prices/`)

Every residential property sale in England & Wales registered with HMLR since 1995.

**Source:** https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads

**S3 path:** `s3://dantelore.data.incoming/house_prices/ppd/year={year}/`

**Glue table:** `incoming.house_prices_ppd`

| Field | Type | Description |
|---|---|---|
| `transaction_id` | string | Unique transaction identifier |
| `price` | bigint | Sale price in £ |
| `date_of_transfer` | string | Date of sale (YYYY-MM-DD HH:MM) |
| `postcode` | string | Property postcode |
| `property_type` | string | `D` detached, `S` semi-detached, `T` terraced, `F` flat, `O` other |
| `old_new` | string | `Y` newly built, `N` established residential |
| `duration` | string | `F` freehold, `L` leasehold |
| `paon` | string | Primary addressable object name (house number or name) |
| `saon` | string | Secondary addressable object name (flat/unit within building) |
| `street` | string | Street name |
| `locality` | string | Locality |
| `town_city` | string | Town or city |
| `district` | string | District |
| `county` | string | County |
| `ppd_category_type` | string | `A` standard, `B` additional (non-standard/bulk transfers) |
| `record_status` | string | `A` addition, `C` change, `D` delete |
| `year` | string | **Partition key** — year of transfer (e.g. `2023`) |

**Load 1995 to present:**
```bash
python house_prices/house_prices_bulk_load.py --start 1995
```

**Load a specific year range:**
```bash
python house_prices/house_prices_bulk_load.py --start 2020 --end 2024
```

**When to re-run:** New data is published monthly. Re-run with `--start <year> --end <year>`
for the current year to pick up new transactions.

---

### 3. ONS Built-up Area Boundaries 2024 (`ons_bua_boundaries/`)

Polygon boundaries for all 7,775 Built-up Areas (BUAs) in England and Wales,
as defined by the ONS in April 2024. Useful as a reference geometry for spatial
filtering and joining against other datasets (e.g. house prices, traffic census).

**Source:** ONS Open Geography Portal — `main_ONS_BUA_2024_EW_V2` ArcGIS FeatureServer

**S3 path:** `s3://dantelore.data.incoming/ons_bua_boundaries/bua/bua_2024.parquet`

**Glue table:** `incoming.ons_bua_boundaries_bua`

| Field | Type | Description |
|---|---|---|
| `bua24cd` | string | Stable ONS area code (primary key, e.g. `E63012319`) |
| `bua24nm` | string | Area name (e.g. `Newbury`) |
| `geometry_wgs84_wkt` | string | Polygon/MultiPolygon in WGS84 (EPSG:4326, lng/lat) as WKT |
| `geometry_osgb_wkt` | string | Polygon/MultiPolygon in British National Grid (EPSG:27700, metres) as WKT |
| `centre_e` | int | Centroid easting (OSGB metres) |
| `centre_n` | int | Centroid northing (OSGB metres) |
| `bbox_min_e` | int | Bounding rectangle min easting (OSGB metres) |
| `bbox_min_n` | int | Bounding rectangle min northing (OSGB metres) |
| `bbox_max_e` | int | Bounding rectangle max easting (OSGB metres) |
| `bbox_max_n` | int | Bounding rectangle max northing (OSGB metres) |

**Load (replaces the single parquet file with the full current dataset):**
```bash
python ons_bua_boundaries/ons_bua_boundaries_load.py
```

**When to re-run:** ONS BUA boundaries are updated infrequently (last revision April 2024).
Re-run when a new vintage is published on the Open Geography Portal.

---

### 4. OS Code Point Open (`os_code_point_open/`)

Coordinates and administrative codes for every postcode in Great Britain (~1.8 million postcodes),
partitioned by postcode area (e.g. `RG`, `SW`). Useful for joining house price or traffic data
to geographic areas via postcode.

**Source:** https://osdatahub.os.uk/downloads/open/CodePointOpen

**S3 path:** `s3://dantelore.data.incoming/os_code_point_open/codepo/postcode_area={area}/`

**Glue table:** `incoming.os_code_point_open_codepo`

| Field | Type | Description |
|---|---|---|
| `postcode` | string | Full postcode (e.g. `RG14 5RU`) |
| `positional_quality_indicator` | int | Accuracy of the coordinates (1 = best, 9 = worst) |
| `eastings` | int | OSGB easting of postcode centroid (metres) |
| `northings` | int | OSGB northing of postcode centroid (metres) |
| `country_code` | string | Country code (e.g. `E92000001` for England) |
| `nhs_regional_ha_code` | string | NHS Regional Health Authority code |
| `nhs_ha_code` | string | NHS Health Authority code |
| `admin_county_code` | string | Administrative county code |
| `admin_district_code` | string | Administrative district code |
| `admin_ward_code` | string | Administrative ward code |
| `postcode_area` | string | **Partition key** — leading letters of postcode, lowercase (e.g. `rg`) |

**Load (overwrites existing data with current release):**
```bash
python os_code_point_open/os_code_point_open_load.py
```

**When to re-run:** OS publish updated data quarterly.

---

### 5. OS Open UPRN (`os_open_uprn/`)

Coordinates for every addressable location in Great Britain, each identified by a
Unique Property Reference Number (UPRN). ~40 million records.

**Source:** https://osdatahub.os.uk/downloads/open/OpenUPRN

**S3 path:** `s3://dantelore.data.incoming/os_open_uprn/uprn/grid_e={e}/grid_n={n}/`

**Glue table:** `incoming.os_open_uprn_uprn`

| Field | Type | Description |
|---|---|---|
| `uprn` | bigint | Unique Property Reference Number |
| `x_coordinate` | double | OSGB easting (metres) |
| `y_coordinate` | double | OSGB northing (metres) |
| `latitude` | double | WGS84 latitude |
| `longitude` | double | WGS84 longitude |
| `grid_e` | int | **Partition key** — `floor(x_coordinate / 100000)`, 100km easting tile |
| `grid_n` | int | **Partition key** — `floor(y_coordinate / 100000)`, 100km northing tile |

**Load (overwrites existing data with current release):**
```bash
python os_open_uprn/os_open_uprn_load.py
```

**When to re-run:** OS publish updated data every six weeks.

---

### 6. VOA 2026 Compiled Rating List (`voa_rating_list/`)

All non-domestic (commercial) rated properties in England and Wales from the 2026
Valuation Office Agency compiled rating list. ~2.4 million entries covering shops,
offices, warehouses, factories, pubs and all other business premises.

Useful as a count of commercial addresses within an area — subtract from total UPRN
count to estimate the residential address count.

**Source:** https://voaratinglists.blob.core.windows.net/html/rlidata.htm
(Free to download; usage subject to VOA terms and conditions)

**S3 path:** `s3://dantelore.data.incoming/voa_rating_list/entries/postcode_area={area}/`

**Glue table:** `incoming.voa_rating_list_entries`

| Field | Type | Description |
|---|---|---|
| `uarn` | string | Unique Address Reference Number — VOA's property identifier (alphanumeric) |
| `ba_code` | string | Billing authority (local council) code |
| `ndr_community_code` | string | NDR community code |
| `desc_code` | string | Property type code (e.g. `CS` = shop, `CO` = offices, `IF` = factory) |
| `desc_text` | string | Property type description (e.g. `SHOP AND PREMISES`) |
| `assessment_reference` | bigint | Internal VOA assessment reference |
| `full_address` | string | Full address as a single concatenated string |
| `number_or_name` | string | Property number or name |
| `street` | string | Street name |
| `town` | string | Town |
| `postal_district` | string | Postal district |
| `county` | string | County |
| `postcode` | string | Full postcode (e.g. `RG14 5RU`) |
| `effective_date` | string | Date the entry became effective (DD-MON-YYYY) |
| `rateable_value` | int | Rateable value in £ |
| `appeal_settlement_code` | string | Appeal status code |
| `ba_reference` | string | Billing authority's own reference for this property |
| `list_alteration_date` | string | Date the list entry was last altered (DD-MON-YYYY) |
| `scat_code` | string | Special Category code — more granular classification than `desc_code` |
| `sub_street_1` | string | Sub-street address level 1 (e.g. building name) |
| `sub_street_2` | string | Sub-street address level 2 (e.g. floor) |
| `sub_street_3` | string | Sub-street address level 3 (e.g. unit) |
| `case_number` | bigint | Appeal case number if applicable |
| `current_from_date` | string | Date the current rateable value took effect (DD-MON-YYYY) |
| `postcode_area` | string | **Partition key** — leading letters of postcode, lowercase (e.g. `rg`) |

**Load:**
```bash
python voa_rating_list/voa_rating_list_load.py
```

**When to re-run:** The VOA publish change updates twice weekly. The baseline epoch
used here is `0001` (2026 list) — check the download portal for newer epochs and update
`DOWNLOAD_URL` in the loader accordingly.

---

### 7. ONS Inflation (`ons_inflation/`)

Monthly CPI, CPIH and RPI time series from the ONS MM23 dataset. 934 monthly
observations from June 1948 (RPI) and January 1988 (CPI/CPIH) to present.
Useful for deflating house prices or other monetary values to real terms.

**Source:** ONS MM23 dataset via `www.ons.gov.uk` time series API (no authentication required)

**S3 path:** `s3://dantelore.data.incoming/ons_inflation/inflation/inflation.parquet`

**Glue table:** `incoming.ons_inflation_inflation`

| Field | Type | Description |
|---|---|---|
| `year` | int | Year |
| `month` | int | Month number (1–12) |
| `cpi_index` | double | CPI index value (2015=100), from Jan 1988 |
| `cpi_rate` | double | CPI 12-month rate % (year-on-year), from Jan 1989 |
| `cpih_index` | double | CPIH index value (2015=100), from Jan 1989 |
| `cpih_rate` | double | CPIH 12-month rate % (year-on-year), from Jan 1988 |
| `rpi_rate` | double | RPI 12-month rate % (year-on-year), from Jun 1948 |

**Load (replaces the single parquet file with all series up to the latest published month):**
```bash
python ons_inflation/ons_inflation_load.py
```

**When to re-run:** ONS publish updated inflation figures monthly (typically around the 3rd Wednesday).

---

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

Ensure the `dantelore` AWS profile is configured with access to:
- `s3://dantelore.data.incoming`
- `s3://dantelore.queryresults`
- Glue / Athena

## Deploy Glue tables

```bash
cd terraform
terraform init
terraform apply
```

Or from the root:
```bash
./build.sh
```
