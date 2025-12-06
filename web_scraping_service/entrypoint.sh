#!/bin/bash
set -e

AIRFLOW_UID=$(id -u airflow 2>/dev/null || echo "50000")
AIRFLOW_GID=$(id -g airflow 2>/dev/null || echo "0")

if [ "$(id -u)" = "0" ]; then
    mkdir -p /opt/airflow/logs/scheduler
    mkdir -p /opt/airflow/logs/dag_processor_manager
    
    CURRENT_DATE=$(date +%Y-%m-%d)
    mkdir -p /opt/airflow/logs/scheduler/${CURRENT_DATE} || true
    
    chown -R ${AIRFLOW_UID}:${AIRFLOW_GID} /opt/airflow/logs 2>/dev/null || true
    chmod -R 775 /opt/airflow/logs 2>/dev/null || true
    
    exec gosu airflow "$@"
else
    mkdir -p /opt/airflow/logs/scheduler || true
    mkdir -p /opt/airflow/logs/dag_processor_manager || true
    
    exec "$@"
fi

