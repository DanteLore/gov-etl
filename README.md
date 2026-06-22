# gov-etl

ETL pipelines loading UK government datasets into the dantelore S3 data lake
(`dantelore.data.incoming`), queryable via Athena.

## Conventions

### Spatial partitioning

Point and raster datasets with OSGB36 coordinates use a consistent two-key partition scheme:

| Partition key | Derivation | Range |
|---|---|---|
| `grid_e` | `floor(x_coordinate / 100000)` | 0–6 (100km easting tiles) |
| `grid_n` | `floor(y_coordinate / 100000)` | 0–12 (100km northing tiles) |

This matches the OS National Grid 100km squares (SV → HZ). Coordinate columns are always
named `x_coordinate` (easting) and `y_coordinate` (northing) in OSGB36 metres (EPSG:27700).

Datasets covering all of Great Britain have up to 91 tile combinations; England-only datasets
cover a subset. Querying a specific area requires filtering on both `grid_e` and `grid_n` to
get partition pruning.

Postcode-anchored datasets (house prices, VOA, Code Point Open, postcode lookup) use
`postcode_area` (e.g. `sw`, `rg`) instead, as their natural join key is the postcode.

## Datasets

Dataset documentation lives in the **data catalogue**, which is maintained as a
[git subtree](https://www.atlassian.com/git/tutorials/git-subtree) under `catalogue/`.
The subtree tracks a separate repository (`dantelore/catalogue`) that follows the
[World's Simplest Data Catalogue](https://github.com/dantelore/wsdc) convention —
one Markdown file per dataset, a shared index, and no tooling required to read it.

The gov-etl entries live under `catalogue/gov-etl/`:

- **[catalogue/gov-etl/README.md](catalogue/gov-etl/README.md)** — full dataset list with table names and one-line descriptions
- **[catalogue/index.md](catalogue/index.md)** — top-level index across all catalogued systems

Each dataset file contains: description, location (S3 + Glue table), field spec, common
Athena queries, source ETL script, and known caveats.

To push catalogue changes back to the upstream catalogue repo:
```bash
git subtree push --prefix=catalogue catalogue main
```

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
