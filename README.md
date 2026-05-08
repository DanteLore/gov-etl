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

### 3. OS Open UPRN (`os_open_uprn/`)

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

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows
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
