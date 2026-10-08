"""Ingest: get new data INTO bronze (extract + load). Nothing else.

The pipeline has two halves with two tools:
  1. Python gets data in:        ECB API -> raw file -> bronze     (this file)
  2. dbt transforms and tests:   bronze -> silver -> gold          (the dbt/ folder)

Run:  uv run python -m pipeline.ingest
Then: cd dbt
      uv run dbt build
"""

from datetime import timedelta

import duckdb

from pipeline.config import Config, load_config
from pipeline.extract import fetch_rates, save_raw
from pipeline.load import connect, create_bronze, latest_loaded_date, load_new_files


def incremental_start(con: duckdb.DuckDBPyConnection, cfg: Config) -> str:
    """Where should this run start fetching?

    First run (bronze empty): from start_period in the config.
    Later runs: a few days BEFORE the newest date we have (the lookback), so
    corrections the ECB made to recent days are picked up. Silver keeps the newest copy.
    """
    latest = latest_loaded_date(con)
    if latest is None:
        return cfg.start_period
    return (latest - timedelta(days=cfg.lookback_days)).isoformat()


def ingest(con: duckdb.DuckDBPyConnection, cfg: Config) -> int:
    """Fetch new rates, save the raw file, load it into bronze. Returns the new rows."""
    print("1. EXTRACT")
    start = incremental_start(con, cfg)
    text = fetch_rates(cfg, start)
    if text is None:
        print("  no new data from the ECB")
    else:
        path = save_raw(text, cfg)
        print(f"  saved {len(text.splitlines()) - 1} rows to {path.name}")

    print("2. LOAD")
    n_new = load_new_files(con, cfg)
    print(f"  {n_new} new rows in bronze")
    return n_new


if __name__ == "__main__":
    cfg = load_config()
    con = connect(cfg)
    create_bronze(con)
    ingest(con, cfg)
    # Close the connection: DuckDB allows one writer at a time, and dbt is next
    con.close()
    print("Bronze is up to date. Next: cd dbt, then uv run dbt build")
