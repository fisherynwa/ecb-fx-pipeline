"""Tests for pipeline/export.py and the dashboard's Parquet fallback."""

import pandas as pd

from app import data
from pipeline.export import export_gold


def test_export_writes_one_parquet_file_per_gold_table(gold_db, tmp_path):
    out = tmp_path / "published"

    counts = export_gold(gold_db, out)

    assert counts == {"fx_daily": 6, "fx_monthly": 1}
    assert sorted(p.name for p in out.iterdir()) == [
        "fx_daily.parquet",
        "fx_monthly.parquet",
    ]


def test_dashboard_reads_the_same_data_from_parquet(gold_db, tmp_path):
    # The Parquet fallback must give the dashboard exactly what the warehouse gives
    out = tmp_path / "published"
    export_gold(gold_db, out)

    daily, monthly = data.load_published(out)

    pd.testing.assert_frame_equal(daily, data.load_daily(gold_db))
    pd.testing.assert_frame_equal(monthly, data.load_monthly(gold_db))


def test_export_is_stable_when_nothing_changes(gold_db, tmp_path):
    # Same data -> byte-identical files, so git only records real updates
    first, second = tmp_path / "a", tmp_path / "b"
    export_gold(gold_db, first)
    export_gold(gold_db, second)

    for name in ("fx_daily.parquet", "fx_monthly.parquet"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
