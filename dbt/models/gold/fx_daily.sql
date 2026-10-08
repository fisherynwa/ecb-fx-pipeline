-- Gold: daily rates with returns and rolling volatility, one row per currency and day.
--
-- lag() puts the previous publication day next to each row (Friday -> Monday,
-- not the previous calendar day). The volatility window size comes from
-- var('vol_window_days') in dbt_project.yml.

{% set window_days = var('vol_window_days') %}

WITH with_previous AS (
    SELECT
        rate_date,
        currency,
        units_per_eur,
        -- previous day's rate of the SAME currency (PARTITION BY), in date order
        lag(units_per_eur) OVER (
            PARTITION BY currency
            ORDER BY rate_date
        ) AS prev_units_per_eur
    FROM {{ ref('ecb_rates') }}
),

with_returns AS (
    SELECT
        *,
        units_per_eur / prev_units_per_eur - 1   AS daily_return,  -- 0.002 = +0.2 %
        ln(units_per_eur / prev_units_per_eur)   AS log_return     -- used for volatility
    FROM with_previous
)

SELECT
    rate_date,
    currency,
    units_per_eur,
    prev_units_per_eur,
    daily_return,
    log_return,
    -- Standard deviation of the last N daily log returns, scaled to a year.
    -- NULL until N returns are available.
    CASE
        WHEN count(log_return) OVER last_n = {{ window_days }}
        THEN stddev_samp(log_return) OVER last_n
             * sqrt({{ var('trading_days_per_year') }})
    END AS volatility_20d
FROM with_returns
WINDOW last_n AS (
    PARTITION BY currency
    ORDER BY rate_date
    ROWS BETWEEN {{ window_days - 1 }} PRECEDING AND CURRENT ROW
)
ORDER BY currency, rate_date
