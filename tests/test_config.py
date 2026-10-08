"""Tests for pipeline/config.py: is config.yaml read correctly?"""

import dataclasses

import pytest

from pipeline.config import PROJECT_ROOT, load_config

YAML = """
api:
  base_url: https://example.test/service/data
  dataset: EXR
  timeout_seconds: 30
currencies: [usd, gbp]
start_period: "2026-01-01"
paths:
  raw_dir: data/raw
  database: data/warehouse.duckdb
"""


def test_load_config_reads_the_yaml(tmp_path):
    # Arrange: write a small config file
    path = tmp_path / "config.yaml"
    path.write_text(YAML, encoding="utf-8")

    # Act
    cfg = load_config(path)

    # Assert
    assert cfg.dataset == "EXR"
    assert cfg.timeout_seconds == 30
    assert cfg.currencies == ["USD", "GBP"]  # lower case in the file, upper case here
    assert cfg.database == PROJECT_ROOT / "data" / "warehouse.duckdb"


def test_missing_optional_settings_get_defaults(tmp_path):
    # The YAML above has no "incremental:" and no "checks:" section
    path = tmp_path / "config.yaml"
    path.write_text(YAML, encoding="utf-8")

    cfg = load_config(path)

    assert cfg.lookback_days == 7
    assert cfg.max_days_stale == 5


def test_config_cannot_be_changed_while_running(cfg):
    # frozen=True: changing a setting must fail loudly
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.currencies = ["JPY"]
