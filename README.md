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

Key columns:
- `bua24cd` — stable ONS area code (primary key)
- `bua24nm` — area name
- `geometry_wgs84_wkt` — polygon in WGS84 (EPSG:4326)
- `geometry_osgb_wkt` — polygon in British National Grid (EPSG:27700)
- `centre_e` / `centre_n` — OSGB centroid (metres)
- `bbox_min_e` / `bbox_min_n` / `bbox_max_e` / `bbox_max_n` — OSGB bounding rectangle (metres)

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

Partitioned by 100km OSGB National Grid tile: `grid_e = floor(X_COORDINATE / 100000)`,
`grid_n = floor(Y_COORDINATE / 100000)`. Covers roughly grid_e 0-6, grid_n 0-12.

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

Partitioned by postcode area (e.g. `rg`, `sw`).

**Load:**
```bash
python voa_rating_list/voa_rating_list_load.py
```

**When to re-run:** The VOA publish change updates twice weekly. The baseline epoch
used here is `0001` (2026 list) — check the download portal for newer epochs and update
`DOWNLOAD_URL` in the loader accordingly.

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
