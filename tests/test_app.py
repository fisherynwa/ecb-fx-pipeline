"""Tests for app/data.py: the dashboard's data functions, without starting Streamlit."""

import duckdb
import pandas as pd
import pytest

from app import data


def test_load_daily_reads_the_gold_table(gold_db):
    daily = data.load_daily(gold_db)

    assert len(daily) == 6
    assert list(daily.columns) == [
        "rate_date", "currency", "units_per_eur", "daily_return", "volatility_20d"
    ]  # fmt: skip


def test_the_dashboard_cannot_change_the_data(gold_db):
    # read_only=True: a query that writes must fail
    with pytest.raises(duckdb.Error):
        data.read_sql(gold_db, "DELETE FROM gold.fx_daily")


def test_latest_per_currency_takes_the_newest_day(gold_db):
    latest = data.latest_per_currency(data.load_daily(gold_db))

    assert latest.loc["USD", "rate_date"] == pd.Timestamp("2026-10-05")
    assert latest.loc["JPY", "units_per_eur"] == 178.5


def test_rebase_to_100_starts_every_currency_at_100(gold_db):
    rebased = data.rebase_to_100(data.load_daily(gold_db))

    index = rebased.set_index(["currency", "rate_date"])["index_100"]

    assert index["USD", pd.Timestamp("2026-10-01")] == 100.0
    assert index["JPY", pd.Timestamp("2026-10-01")] == 100.0
    # USD went from 1.10 to 1.21, which is +10 %, so its index is 110
    assert index["USD", pd.Timestamp("2026-10-02")] == pytest.approx(110.0)


def test_filter_period_counts_back_from_the_newest_date():
    dates = pd.to_datetime(["2026-06-30", "2026-08-31", "2026-09-10", "2026-10-05"])
    daily = pd.DataFrame({"rate_date": dates, "currency": "USD"})

    assert len(data.filter_period(daily, "All")) == 4
    # 1 month before 2026-10-05 is 2026-09-05: keeps 09-10 and 10-05
    assert len(data.filter_period(daily, "1 month")) == 2
    # 3 months before is 2026-07-05: also keeps 08-31
    assert len(data.filter_period(daily, "3 months")) == 3
