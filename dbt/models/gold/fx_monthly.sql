-- Gold: monthly summary, one row per currency and month.

SELECT
    date_trunc('month', rate_date)::DATE     AS month,          -- 2026-09-24 -> 2026-09-01
    currency,
    count(*)                                 AS n_days,         -- ECB publication days
    round(avg(units_per_eur), 4)             AS avg_rate,
    min(units_per_eur)                       AS min_rate,
    max(units_per_eur)                       AS max_rate,
    -- rate on the LAST day of the month: "the rate whose rate_date is the largest"
    arg_max(units_per_eur, rate_date)        AS month_end_rate
FROM {{ ref('ecb_rates') }}
GROUP BY month, currency
ORDER BY currency, month
