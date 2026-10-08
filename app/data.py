"""Read the gold tables for the dashboard, and shape them for the charts.

Kept apart from the Streamlit page (streamlit_app.py), so every function here
can be tested with pytest without starting a web app (tests/test_app.py).
"""

from pathlib import Path

import duckdb
import pandas as pd

PERIODS = {"1 month": 1, "3 months": 3, "6 months": 6, "All": None}
DAILY_COLUMNS = [
    "rate_date",
    "currency",
    "units_per_eur",
    "daily_return",
    "volatility_20d",
]


def read_sql(db_path: Path, sql: str) -> pd.DataFrame:
    """Run one query READ-ONLY and close the connection straight away.

    read_only=True: the dashboard can never change the data.
    Closing at once: DuckDB allows one writer, so the dashboard must not keep the
    file open while the pipeline (or Airflow) wants to write to it.
    """
    with duckdb.connect(str(db_path), read_only=True) as con:
        return con.execute(sql).df()


def load_daily(db_path: Path) -> pd.DataFrame:
    """gold.fx_daily: one row per currency and day."""
    return read_sql(
        db_path,
        """
        SELECT rate_date, currency, units_per_eur, daily_return, volatility_20d
        FROM gold.fx_daily
        ORDER BY currency, rate_date
        """,
    )


def load_monthly(db_path: Path) -> pd.DataFrame:
    """gold.fx_monthly: one row per currency and month."""
    return read_sql(db_path, "SELECT * FROM gold.fx_monthly ORDER BY currency, month")


def read_parquet(path: Path) -> pd.DataFrame:
    """Read one Parquet file with an in-memory DuckDB: no database file involved."""
    with duckdb.connect() as con:
        return con.execute("SELECT * FROM read_parquet(?)", [str(path)]).df()


def load_published(folder: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The same two tables as load_daily and load_monthly, from the Parquet export.

    Used when there is no DuckDB warehouse file, e.g. right after cloning the repo.
    """
    daily = read_parquet(folder / "fx_daily.parquet")[DAILY_COLUMNS]
    monthly = read_parquet(folder / "fx_monthly.parquet")
    daily = daily.sort_values(["currency", "rate_date"], ignore_index=True)
    monthly = monthly.sort_values(["currency", "month"], ignore_index=True)
    return daily, monthly


def latest_per_currency(daily: pd.DataFrame) -> pd.DataFrame:
    """The newest row of each currency, indexed by currency."""
    newest = daily.sort_values("rate_date").groupby("currency").tail(1)
    return newest.set_index("currency")


def filter_period(daily: pd.DataFrame, period: str) -> pd.DataFrame:
    """Keep only the last N months, counted back from the newest date."""
    months = PERIODS[period]
    if months is None:
        return daily
    start = daily["rate_date"].max() - pd.DateOffset(months=months)
    return daily[daily["rate_date"] >= start]


def rebase_to_100(daily: pd.DataFrame) -> pd.DataFrame:
    """Each currency as an index that starts at 100 on the first day shown.

    JPY is around 170 per euro and GBP around 0.87, so on one axis their raw
    rates can't be compared. Rebased, both start at 100 and the lines show
    the relative change: 102 = 2 % more units per euro than at the start.
    Returns long format: rate_date, currency, index_100.
    """
    wide = daily.pivot(index="rate_date", columns="currency", values="units_per_eur")
    first = wide.bfill().iloc[0]  # first available rate of each currency
    rebased = wide.div(first) * 100
    return rebased.reset_index().melt(
        id_vars="rate_date", var_name="currency", value_name="index_100"
    )
