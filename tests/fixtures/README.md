# Test fixtures

`ecb_rates_sample.csv` is a **synthetic** file in the ECB CSV format: four
currencies (USD, GBP, JPY, CHF), June to September 2026, generated as a random
walk with about 0.4 % daily moves. It is not real ECB data.

CI loads it into bronze and runs `dbt build` on it, so the models and data
tests are checked on every push without calling the ECB API.
