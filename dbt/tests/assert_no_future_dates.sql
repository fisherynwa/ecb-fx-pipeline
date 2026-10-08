-- No rate may have a date in the future. Returns the rows that do.

SELECT
    rate_date,
    currency,
    units_per_eur
FROM {{ ref('ecb_rates') }}
WHERE rate_date > current_date
