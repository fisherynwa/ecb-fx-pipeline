"""Daily ECB FX pipeline: ingest -> source freshness -> dbt build.

The same three commands you can run by hand, run by Airflow:
  1. python -m pipeline.ingest      new rates -> bronze
  2. dbt source freshness           is the newest rate recent enough?
  3. dbt build                      silver + gold, with their tests

Runs on weekdays at 17:00 Berlin time, after the ECB publishes (~16:00).
"""

import os
from datetime import timedelta

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

# Where things are inside the container (see docker-compose.yml).
# Read from environment variables, so the DAG can also be tested elsewhere.
PROJECT = os.environ.get("ECB_PROJECT_DIR", "/opt/project")
VENV = os.environ.get("ECB_VENV_BIN", "/opt/pipeline-venv/bin")

with DAG(
    dag_id="ecb_fx_daily",
    description="ECB rates: bronze (Python) -> silver and gold (dbt)",
    schedule="0 17 * * 1-5",  # cron: minute 0, hour 17, Monday to Friday
    start_date=pendulum.datetime(2026, 10, 1, tz="Europe/Berlin"),
    catchup=False,  # don't replay every missed day since start_date
    max_active_runs=1,  # never two runs writing to the database at once
    default_args={
        "retries": 1,  # try a failed task once more, e.g. if the ECB API was down
        "retry_delay": timedelta(minutes=2),
    },
    tags=["ecb", "fx", "dbt"],
) as dag:
    ingest = BashOperator(
        task_id="ingest_to_bronze",
        bash_command=f"{VENV}/python -m pipeline.ingest",
        cwd=PROJECT,  # run from the project folder, as when running it by hand
    )

    freshness = BashOperator(
        task_id="dbt_source_freshness",
        bash_command=f"{VENV}/dbt source freshness",
        cwd=f"{PROJECT}/dbt",
    )

    build = BashOperator(
        task_id="dbt_build",
        bash_command=f"{VENV}/dbt build",
        cwd=f"{PROJECT}/dbt",
    )

    # The order: each task starts only if the one before it succeeded
    ingest >> freshness >> build
