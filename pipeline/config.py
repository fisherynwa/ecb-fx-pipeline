"""Load config.yaml into a typed object.

Usage anywhere in the project:
    from pipeline.config import load_config
    cfg = load_config()
    cfg.currencies      -> ["USD", "GBP"]
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

# The project root is one folder above this file (pipeline/ -> project folder).
# Paths in config.yaml are relative to it, so scripts work from any folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = PROJECT_ROOT / "config.yaml"


@dataclass(frozen=True)  # frozen = settings can't be changed by accident while running
class Config:
    base_url: str
    dataset: str
    timeout_seconds: int
    currencies: list[str]
    start_period: str
    raw_dir: Path
    database: Path
    lookback_days: int
    max_days_stale: int


def load_config(path: Path = CONFIG_FILE) -> Config:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return Config(
        base_url=raw["api"]["base_url"],
        dataset=raw["api"]["dataset"],
        timeout_seconds=raw["api"]["timeout_seconds"],
        currencies=[c.upper() for c in raw["currencies"]],
        start_period=str(raw["start_period"]),
        raw_dir=PROJECT_ROOT / raw["paths"]["raw_dir"],
        database=PROJECT_ROOT / raw["paths"]["database"],
        # .get(..., default): use the default if the setting is missing from the file
        lookback_days=raw.get("incremental", {}).get("lookback_days", 7),
        max_days_stale=raw.get("checks", {}).get("max_days_stale", 5),
    )
