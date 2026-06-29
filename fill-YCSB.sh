#!/bin/bash
set -e

# fill-YCSB.sh
# This script only prepares/fills YCSB RocksDB databases if they do not already exist.
# It does not run baseline or CacheLink experiments.

# =========================
# CONFIG
# =========================
WORKLOADS=(
    "workloads/workloada"
    "workloads/workloadb"
    "workloads/workloadc"
    "workloads/workloadd"
    "workloads/workloadf"
)

RECORDCOUNT=1000000
FIELD_LENGTH=4096
LOAD_THREADS=16

DB_BASE_DIR="/export"
LOG_DIR="/export/logs"

mkdir -p "$LOG_DIR"

cd /workspace/YCSB

# =========================
# MAIN LOOP
# =========================
for WORKLOAD in "${WORKLOADS[@]}"; do

    WORKLOAD_NAME=$(basename "$WORKLOAD")
    DB_PATH="${DB_BASE_DIR}/db1m_${WORKLOAD_NAME}"
    LOG_FILE="${LOG_DIR}/load_${WORKLOAD_NAME}.txt"

    echo "======================================"
    echo "WORKLOAD: $WORKLOAD"
    echo "DB PATH : $DB_PATH"
    echo "LOG FILE: $LOG_FILE"
    echo "======================================"

    if [ ! -d "$DB_PATH" ]; then
        echo "[INFO] Database does not exist. Starting load phase..."

        ./bin/ycsb load rocksdb \
            -threads "$LOAD_THREADS" \
            -s \
            -P "$WORKLOAD" \
            -p rocksdb.dir="$DB_PATH" \
            -p recordcount="$RECORDCOUNT" \
            -p fieldlength="$FIELD_LENGTH" \
            > "$LOG_FILE" 2>&1

        echo "[INFO] Load completed for $WORKLOAD_NAME"
    else
        echo "[INFO] Database already exists. Skipping load: $DB_PATH"
    fi

    echo
done

echo "=== ALL YCSB DATABASE PREPARATION DONE ==="
echo "Logs saved in: $LOG_DIR"
