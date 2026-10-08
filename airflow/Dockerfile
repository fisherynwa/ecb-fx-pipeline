# Airflow image for this project.
# Airflow runs in its own Python environment, and the pipeline code (Python + dbt)
# runs in a SEPARATE virtual environment, /opt/pipeline-venv, so their packages
# can never clash. Airflow only starts commands; it never imports the pipeline.
FROM apache/airflow:3.3.2-python3.12

USER root
COPY requirements-pipeline.txt /tmp/requirements-pipeline.txt
RUN python -m venv /opt/pipeline-venv \
    && /opt/pipeline-venv/bin/pip install --no-cache-dir -r /tmp/requirements-pipeline.txt \
    && rm /tmp/requirements-pipeline.txt

USER airflow
