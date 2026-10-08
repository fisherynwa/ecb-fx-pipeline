-- A singular test: it returns the BAD rows. 0 rows = PASS, any row = FAIL.
-- Silver must hold exactly one rate per currency and day.

SELECT
    currency,
    rate_date,
    count(*) AS n_copies
FROM {{ ref('ecb_rates') }}
GROUP BY currency, rate_date
HAVING count(*) > 1
