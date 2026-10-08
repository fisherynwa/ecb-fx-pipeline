-- Every rate must be a finite, positive number. Returns the rows that are not.

SELECT
    rate_date,
    currency,
    units_per_eur
FROM {{ ref('ecb_rates') }}
WHERE units_per_eur <= 0
   OR NOT isfinite(units_per_eur)
