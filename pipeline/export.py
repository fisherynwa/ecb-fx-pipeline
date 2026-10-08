"""Export: write the gold tables to Parquet files in published/.

The DuckDB warehouse is not in git (data/ is ignored). The gold tables are small,
so they are exported to Parquet and committed instead. The dashboard falls back
to these files when there is no warehouse, e.g. right after cloning the repo.

Run (after dbt build):  uv run python -m pipeline.export
"""

from pathlib import Path

import duckdb

from pipeline.config import load_config

GOLD_TABLES = ["fx_daily", "fx_monthly"]


def export_gold(db_path: Path, out_dir: Path) -> dict[str, int]:
    """Write every gold table to <out_dir>/<table>.parquet. Returns rows per table.

    ORDER BY ALL sorts the rows the same way on every run, so the files only
    change when the data changes, and git only records real updates.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    with duckdb.connect(str(db_path), read_only=True) as con:
        for table in GOLD_TABLES:
            target = (out_dir / f"{table}.parquet").as_posix()
            con.execute(
                f"COPY (SELECT * FROM gold.{table} ORDER BY ALL) "
                f"TO '{target}' (FORMAT parquet)"
            )
            counts[table] = con.execute(
                f"SELECT count(*) FROM gold.{table}"
            ).fetchone()[0]
    return counts


if __name__ == "__main__":
    cfg = load_config()
    for table, n in export_gold(cfg.database, cfg.published_dir).items():
        print(f"  {table}.parquet: {n} rows")
    print(f"Exported to {cfg.published_dir}")
