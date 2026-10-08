"""Load: put raw CSV files into the bronze table in DuckDB.

Bronze = the raw data, as delivered, inside a database:
  * every value is stored as TEXT (VARCHAR), exactly as it was in the file
  * nothing is cleaned, fixed or removed
  * extra "lineage" columns record where each row came from and when

Run:  uv run python -m pipeline.load
"""

from datetime import date
from pathlib import Path

import duckdb

from pipeline.config import Config, load_config

# SQL that creates the bronze table. "IF NOT EXISTS" makes it safe to run every time:
# the first run creates the table, later runs leave it (and its data) alone.
CREATE_BRONZE = """
CREATE SCHEMA IF NOT EXISTS bronze;

CREATE TABLE IF NOT EXISTS bronze.ecb_rates_raw (
    currency        VARCHAR,
    currency_denom  VARCHAR,
    time_period     VARCHAR,   -- a date, but stored as text on purpose
    obs_value       VARCHAR,   -- a number, but stored as text on purpose
    _source_file    VARCHAR,   -- lineage: which raw file this row came from
    _loaded_at      TIMESTAMP DEFAULT current_timestamp  -- lineage: when it was loaded
);
"""


def connect(cfg: Config) -> duckdb.DuckDBPyConnection:
    """Open the DuckDB database file (it's created if it doesn't exist yet)."""
    cfg.database.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(cfg.database))


def create_bronze(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(CREATE_BRONZE)


def load_file(con: duckdb.DuckDBPyConnection, path: Path) -> int:
    """Insert the 4 useful columns of one raw CSV file into bronze. Returns the rows.

    DuckDB reads the CSV itself with read_csv(). all_varchar=true tells it NOT to
    guess types: every value stays text, exactly as in the file.
    The ? placeholders are filled in safely from the list at the end.
    """
    before = con.execute("SELECT count(*) FROM bronze.ecb_rates_raw").fetchone()[0]
    con.execute(
        """
        INSERT INTO bronze.ecb_rates_raw
            (currency, currency_denom, time_period, obs_value, _source_file)
        SELECT CURRENCY, CURRENCY_DENOM, TIME_PERIOD, OBS_VALUE, ?
        FROM read_csv(?, all_varchar = true)
        """,
        [path.name, str(path)],
    )
    after = con.execute("SELECT count(*) FROM bronze.ecb_rates_raw").fetchone()[0]
    return after - before


def is_loaded(con: duckdb.DuckDBPyConnection, filename: str) -> bool:
    """Has this raw file been loaded before? The lineage column tells us."""
    n = con.execute(
        "SELECT count(*) FROM bronze.ecb_rates_raw WHERE _source_file = ?", [filename]
    ).fetchone()[0]
    return n > 0


def load_new_files(con: duckdb.DuckDBPyConnection, cfg: Config) -> int:
    """Load every raw file that is not in bronze yet. Returns the number of new rows.

    This makes the load IDEMPOTENT: running it twice does not load a file twice.
    """
    total = 0
    for path in sorted(cfg.raw_dir.glob("ecb_rates_*.csv")):
        if is_loaded(con, path.name):
            continue
        n = load_file(con, path)
        print(f"  loaded {n:>5} rows from {path.name}")
        total += n
    return total


def latest_loaded_date(con: duckdb.DuckDBPyConnection) -> date | None:
    """The most recent rate date in bronze (None if bronze is empty)."""
    return con.execute(
        "SELECT max(TRY_CAST(time_period AS DATE)) FROM bronze.ecb_rates_raw"
    ).fetchone()[0]


if __name__ == "__main__":
    cfg = load_config()
    con = connect(cfg)
    create_bronze(con)

    n = load_new_files(con, cfg)
    total = con.execute("SELECT count(*) FROM bronze.ecb_rates_raw").fetchone()[0]

    print(f"Loaded {n} new rows into bronze.ecb_rates_raw")
    print(f"The table now has {total} rows in total")
    con.close()
