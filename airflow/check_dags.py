"""Fail if a DAG in airflow/dags has an import error.

Runs inside the Airflow image in CI.
"""

import sys

from airflow.dag_processing.dagbag import DagBag

bag = DagBag(dag_folder=sys.argv[1] if len(sys.argv) > 1 else "/opt/airflow/dags")

if bag.import_errors:
    for path, error in bag.import_errors.items():
        print(f"IMPORT ERROR in {path}:\n{error}", file=sys.stderr)
    sys.exit(1)

if "ecb_fx_daily" not in bag.dag_ids:
    print("DAG ecb_fx_daily not found", file=sys.stderr)
    sys.exit(1)

print(f"OK: ecb_fx_daily loaded with tasks {sorted(bag.dags['ecb_fx_daily'].task_ids)}")
