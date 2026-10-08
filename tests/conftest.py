"""Shared test setup: fixtures that every test file can use.

A FIXTURE is a function that prepares something a test needs. A test asks for it
by naming it as an argument: def test_x(cfg): ...  -> pytest calls cfg() first.

tmp_path is a fixture built into pytest: a fresh, empty folder for each test,
deleted automatically. Tests never touch your real data/ folder.
"""

import duckdb
import pytest

from pipeline.config import Config
from pipeline.load import connect, create_bronze

# What the ECB sends: a CSV with Windows line endings (\r\n), 2 currencies x 2 days
SAMPLE_CSV = (
    "KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE\r\n"
    "EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-10-01,1.1712\r\n"
    "EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-10-02,1.1730\r\n"
    "EXR.D.GBP.EUR.SP00.A,D,GBP,EUR,SP00,A,2026-10-01,0.8721\r\n"
    "EXR.D.GBP.EUR.SP00.A,D,GBP,EUR,SP00,A,2026-10-02,0.8715\r\n"
)


@pytest.fixture
def sample_csv() -> str:
    """The text of a small ECB response."""
    return SAMPLE_CSV


@pytest.fixture
def cfg(tmp_path) -> Config:
    """A test configuration that points to a temporary folder."""
    return Config(
        base_url="https://example.test/service/data",
        dataset="EXR",
        timeout_seconds=5,
        currencies=["USD", "GBP"],
        start_period="2026-01-01",
        raw_dir=tmp_path / "raw",
        database=tmp_path / "test.duckdb",
        lookback_days=7,
        max_days_stale=5,
    )


@pytest.fixture
def con(cfg):
    """An empty bronze table in a temporary DuckDB file.

    Code after "yield" runs when the test is finished: the clean-up.
    """
    connection = connect(cfg)
    create_bronze(connection)
    yield connection
    connection.close()


@pytest.fixture
def raw_file(cfg):
    """One raw file in the raw folder, as extract would save it."""
    cfg.raw_dir.mkdir(parents=True)
    path = cfg.raw_dir / "ecb_rates_20261002_170000.csv"
    path.write_text(SAMPLE_CSV, encoding="utf-8", newline="")
    return path


@pytest.fixture
def gold_db(tmp_path):
    """A tiny warehouse with the two gold tables: 2 currencies x 3 days."""
    # Not "gold.duckdb": DuckDB names the database after its file, and a database
    # called "gold" would clash with the schema "gold"
    path = tmp_path / "warehouse.duckdb"
    with duckdb.connect(str(path)) as con:
        con.execute("CREATE SCHEMA gold")
        con.execute(
            """
            CREATE TABLE gold.fx_daily AS
            SELECT * FROM (VALUES
                (DATE '2026-10-01', 'USD', 1.10,  NULL,    NULL),
                (DATE '2026-10-02', 'USD', 1.21,  0.10,    NULL),
                (DATE '2026-10-05', 'USD', 1.10,  -0.0909, NULL),
                (DATE '2026-10-01', 'JPY', 170.0, NULL,    NULL),
                (DATE '2026-10-02', 'JPY', 175.1, 0.03,    NULL),
                (DATE '2026-10-05', 'JPY', 178.5, 0.0194,  NULL)
            ) AS t(rate_date, currency, units_per_eur, daily_return, volatility_20d)
            """
        )
        con.execute(
            "CREATE TABLE gold.fx_monthly AS "
            "SELECT DATE '2026-10-01' AS month, 'USD' AS currency"
        )
    return path
