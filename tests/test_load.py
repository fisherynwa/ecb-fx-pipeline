"""Tests for pipeline/load.py, on a temporary DuckDB file."""

from datetime import date

from pipeline.load import latest_loaded_date, load_file, load_new_files


def test_load_file_keeps_every_value_as_text(con, raw_file):
    n = load_file(con, raw_file)

    assert n == 4
    rows = con.execute(
        "SELECT currency, time_period, obs_value, _source_file "
        "FROM bronze.ecb_rates_raw ORDER BY currency, time_period"
    ).fetchall()
    # bronze = exactly what was delivered: '1.1730' stays the text '1.1730'
    assert rows[-1] == ("USD", "2026-10-02", "1.1730", raw_file.name)


def test_loading_twice_does_not_duplicate(con, cfg, raw_file):
    # Idempotency: a file that is already in bronze is skipped
    first = load_new_files(con, cfg)
    second = load_new_files(con, cfg)

    assert first == 4
    assert second == 0
    assert con.execute("SELECT count(*) FROM bronze.ecb_rates_raw").fetchone()[0] == 4


def test_latest_loaded_date(con, raw_file):
    assert latest_loaded_date(con) is None  # empty bronze

    load_file(con, raw_file)

    assert latest_loaded_date(con) == date(2026, 10, 2)
