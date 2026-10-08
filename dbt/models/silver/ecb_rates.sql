-- Silver: clean, typed, deduplicated rates. One row per currency and day.
--
-- Bronze keeps every delivery as text, including the copies created by the
-- lookback window. Here each value gets its real type (TRY_CAST: unreadable
-- values become NULL and are dropped), and only the newest load of each
-- currency and day is kept.

WITH typed AS (
    SELECT
        upper(trim(currency))            AS currency,
        TRY_CAST(time_period AS DATE)    AS rate_date,
        TRY_CAST(obs_value AS DOUBLE)    AS rate,
        _source_file,
        _loaded_at
    FROM {{ source('bronze', 'ecb_rates_raw') }}
    WHERE currency_denom = 'EUR'
),

ranked AS (
    SELECT
        *,
        -- number the copies of each currency + day, newest load first
        row_number() OVER (
            PARTITION BY currency, rate_date
            ORDER BY _loaded_at DESC
        ) AS copy_number
    FROM typed
)

SELECT
    rate_date,
    currency,
    rate          AS units_per_eur,
    _source_file  AS source_file,
    _loaded_at    AS loaded_at
FROM ranked
WHERE copy_number = 1          -- keep the newest copy only
  AND rate_date IS NOT NULL    -- drop rows whose date could not be read
  AND rate IS NOT NULL         -- drop rows whose rate could not be read
ORDER BY currency, rate_date
