# ONS Postcode Lookup

## Description

Lookup table mapping every live postcode in England and Wales to its
administrative geographies: MSOA, local authority district (LAD), county/unitary
authority (CTYUA), region, and country. Useful for answering "what local
authority is postcode X in" or for aggregating postcode-level data to any of
these higher geographies. Sourced from the ONS ArcGIS FeatureServer. Covers
approximately 2.35 million postcodes.

## Classification

Public. Open government data; no personal data.

## Owner

Dan. See gov-etl repo for the code.

## Source & references

ONS ArcGIS FeatureServer:
`Postcode_to_OA_(2021)_to_LSOA_to_MSOA_to_LAD_to_CTYUA_to_RGN_to_CTRY_Best_Fit_Lookup_in_EW`

Boundary vintages: MSOA 2021, LAD 2022, CTYUA 2022, RGN 2022.

## License & usage restrictions

Open Government Licence v3.0. Free to use, share and adapt with attribution
to ONS.

## Location

- S3: `s3://dantelore.data.incoming/ons_postcode_lookup/lookup/postcode_area=<xx>/`
- Glue: `incoming.ons_postcode_lookup_lookup`
- Format: Parquet, partitioned by `postcode_area` (lowercase postcode district
  letters, e.g. `rg`, `sw`)

## Field spec

| Field name | Type | Nullable | Key role | Description |
|---|---|---|---|---|
| postcode | string | No | Primary | Full postcode as returned by ONS (may include space) |
| postcode_area | string | No | Partition key | Lowercase leading letters of postcode, e.g. `rg` |
| msoa21cd | string | Yes | Joins to MSOA boundaries | MSOA 2021 code |
| msoa21nm | string | Yes | | MSOA 2021 name |
| lad22cd | string | Yes | | Local authority district code (2022) |
| lad22nm | string | Yes | | Local authority district name |
| ctyua22cd | string | Yes | | County/unitary authority code (2022) |
| ctyua22nm | string | Yes | | County/unitary authority name |
| rgn22cd | string | Yes | | Region code (2022) |
| rgn22nm | string | Yes | | Region name |
| ctry22cd | string | Yes | | Country code |
| ctry22nm | string | Yes | | Country name |

## Source ETL / code

`github.com/dantelore/gov-etl`, `ons_postcode_lookup/ons_postcode_lookup_load.py`.
One-off script, not scheduled. Fetches all ~2.35M records from the ArcGIS
FeatureServer in parallel (8 workers, 1000 records per page), then uploads
partitioned Parquet files.

## Freshness & update cadence

Loaded on demand; no automatic refresh. The ONS releases updated boundary
lookups periodically - check ONS Open Geography Portal for new versions before
relying on this for anything boundary-sensitive.

## Known issues & caveats

- England and Wales only - no Scotland or Northern Ireland postcodes.
- Boundary vintages are mixed: MSOA 2021, LAD/CTYUA/RGN 2022. Joining to
  datasets that use different boundary vintages will silently produce wrong
  results.
- Some geography fields are nullable; postcodes with no assigned geography
  (e.g. non-geographic postcodes) will have nulls in the code/name fields.
- The ArcGIS service caps pages at 1,000 records; the ETL works around this
  with concurrent pagination.

## Interested parties

| Consumer | Contact | Notes |
|---|---|---|

## Status

Active.
