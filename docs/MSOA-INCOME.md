# ONS MSOA Income Estimates

Modelled household income estimates for all 7,264 Middle Layer Super Output Areas (MSOAs)
in England and Wales, financial year ending March 2023. Published by ONS as part of the
Small Area Income Estimates series.

Four income measures are provided, each with upper/lower confidence limits:

- **Total annual income** — gross household income before tax
- **Net annual income** — disposable (post-tax, post-benefit) household income
- **Net income before housing costs** — equivalised disposable income, housing costs excluded
- **Net income after housing costs** — equivalised disposable income, housing costs deducted

"Equivalised" means adjusted for household size/composition so that a single person and a
family of four with the same raw income are comparable.

## Schema

**Glue table:** `incoming.ons_msoa_income_income`
**S3 location:** `s3://dantelore.data.incoming/ons_msoa_income/income/msoa_income_2023.parquet`

| Column | Type | Description |
|---|---|---|
| `msoa21cd` | string | MSOA code (primary key, e.g. `E02003552`) |
| `msoa21nm` | string | MSOA name |
| `lad_code` | string | Local Authority District code |
| `lad_name` | string | Local Authority District name |
| `rgn_code` | string | Region code |
| `rgn_name` | string | Region name |
| `total_annual_income` | double | Total gross household income (£) |
| `total_annual_income_upper_ci` | double | Upper 95% confidence limit (£) |
| `total_annual_income_lower_ci` | double | Lower 95% confidence limit (£) |
| `total_annual_income_ci` | double | Confidence interval half-width (£) |
| `net_annual_income` | double | Disposable net household income (£) |
| `net_annual_income_upper_ci` | double | Upper 95% confidence limit (£) |
| `net_annual_income_lower_ci` | double | Lower 95% confidence limit (£) |
| `net_annual_income_ci` | double | Confidence interval half-width (£) |
| `net_income_before_housing` | double | Equivalised net income before housing costs (£) |
| `net_income_before_housing_upper_ci` | double | Upper 95% confidence limit (£) |
| `net_income_before_housing_lower_ci` | double | Lower 95% confidence limit (£) |
| `net_income_before_housing_ci` | double | Confidence interval half-width (£) |
| `net_income_after_housing` | double | Equivalised net income after housing costs (£) |
| `net_income_after_housing_upper_ci` | double | Upper 95% confidence limit (£) |
| `net_income_after_housing_lower_ci` | double | Lower 95% confidence limit (£) |
| `net_income_after_housing_ci` | double | Confidence interval half-width (£) |

## Which measure to use

- **`net_income_after_housing`** — best proxy for disposable living standards; accounts for
  both tax/benefits and housing costs. Use this when comparing affordability across areas.
- **`net_annual_income`** — useful when housing costs are separately modelled (e.g. joining
  to house price data to compute affordability ratios).
- **`total_annual_income`** — gross income; use when benchmarking against pre-tax earnings data.
- **Confidence intervals** — MSOAs with wide CIs (large `_ci` values relative to the estimate)
  have high uncertainty; treat those figures with caution.

## Common queries

### Highest income MSOAs nationally

```sql
SELECT msoa21nm, lad_name, rgn_name,
       ROUND(net_annual_income) AS net_income,
       ROUND(net_income_after_housing) AS net_after_housing
FROM ons_msoa_income_income
ORDER BY net_annual_income DESC
LIMIT 20
```

### Income distribution within a local authority

```sql
SELECT
    msoa21nm,
    ROUND(net_annual_income)       AS net_income,
    ROUND(net_income_after_housing) AS net_after_housing,
    ROUND(net_annual_income_ci)     AS uncertainty
FROM ons_msoa_income_income
WHERE lad_name = 'West Berkshire'
ORDER BY net_annual_income DESC
```

### Regional average incomes

```sql
SELECT
    rgn_name,
    ROUND(AVG(net_annual_income))       AS avg_net_income,
    ROUND(AVG(net_income_after_housing)) AS avg_net_after_housing,
    COUNT(*) AS msoa_count
FROM ons_msoa_income_income
GROUP BY rgn_name
ORDER BY avg_net_income DESC
```

### House price to income ratio by MSOA

Join house prices (via postcode lookup) to income estimates to compute affordability:

```sql
SELECT
    i.msoa21nm,
    i.lad_name,
    ROUND(approx_percentile(p.price, 0.5)) AS median_house_price,
    ROUND(i.net_annual_income)             AS net_household_income,
    ROUND(approx_percentile(p.price, 0.5) / i.net_annual_income, 1) AS price_to_income_ratio
FROM house_prices_ppd p
JOIN ons_postcode_lookup_lookup l
    ON p.postcode = l.postcode
    AND l.postcode_area = LOWER(REGEXP_EXTRACT(p.postcode, '^([A-Za-z]+)'))
JOIN ons_msoa_income_income i ON l.msoa21cd = i.msoa21cd
WHERE p.year = '2023'
  AND i.lad_name = 'West Berkshire'
GROUP BY i.msoa21nm, i.lad_name, i.net_annual_income
ORDER BY price_to_income_ratio DESC
```

### Income vs rural-urban classification

```sql
SELECT
    b.ruc21nm,
    COUNT(*) AS msoa_count,
    ROUND(AVG(i.net_annual_income))       AS avg_net_income,
    ROUND(AVG(i.net_income_after_housing)) AS avg_net_after_housing
FROM ons_msoa_income_income i
JOIN ons_msoa_boundaries_msoa b ON i.msoa21cd = b.msoa21cd
GROUP BY b.ruc21nm
ORDER BY avg_net_income DESC
```

## Source and update cadence

**Source:** ONS Small Area Income Estimates for MSOAs, England and Wales —
financial year ending 2023. Published December 2025.

ONS publish updated estimates every 2–3 years. When a new edition is available, update
`DOWNLOAD_URL` in the loader to point to the new file and re-run.

**Reload:**
```bash
python ons_msoa_income/ons_msoa_income_load.py
```
