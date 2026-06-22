# gov-etl

Datasets produced by the [gov-etl](https://github.com/dantelore/gov-etl) pipeline. Open government data from UK public bodies - ONS, HM Land Registry, and others. All datasets are public and licensed under the Open Government Licence unless noted otherwise in the individual entry.

All datasets land in S3 under `s3://dantelore.data.incoming/` and are queryable via Athena (`incoming` database).

## Datasets

| Dataset | Description |
|---|---|
| [ons_postcode_lookup](ons_postcode_lookup.md) | ONS lookup mapping ~2.35M England & Wales postcodes to MSOA, local authority, region, and country |
| [house_prices](house_prices.md) | Every residential property sale registered with HM Land Registry in England & Wales since 1995 |
