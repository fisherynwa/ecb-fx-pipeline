-- A daily move above 10 % is almost certainly a data error, but it COULD be real.
-- severity = 'warn': dbt reports it, and the run still succeeds.

{{ config(severity = 'warn') }}

SELECT
    rate_date,
    currency,
    daily_return
FROM {{ ref('fx_daily') }}
WHERE abs(daily_return) > 0.10
