"""Tests for pipeline/ingest.py: where does an incremental run start?"""

import dataclasses

from pipeline.ingest import incremental_start
from pipeline.load import load_file


def test_first_run_starts_at_start_period(con, cfg):
    # Bronze is empty -> fetch everything from the configured start date
    assert incremental_start(con, cfg) == "2026-01-01"


def test_later_runs_start_one_lookback_before_the_newest_date(con, cfg, raw_file):
    load_file(con, raw_file)  # newest date in bronze: 2026-10-02

    # 2026-10-02 minus 7 days (lookback_days in the test config)
    assert incremental_start(con, cfg) == "2026-09-25"


def test_lookback_comes_from_the_config(con, cfg, raw_file):
    load_file(con, raw_file)  # newest date in bronze: 2026-10-02
    cfg = dataclasses.replace(cfg, lookback_days=3)  # a copy with a 3-day lookback

    # 2026-10-02 minus 3 days
    assert incremental_start(con, cfg) == "2026-09-29"
