#!/bin/bash
set -e

# A: 50% read, 50% update
# B: 95% read, 5% update
# C: 100% read
# D: 95% read, 5% insert (latest)
# E: 95% scan, 5% insert
# F: 50% read-modify-write, 50% read

# =========================
# CONFIG
# =========================
POLICIES=(LRU LRU2Q TinyLFU)
WORKLOADS=("workloads/workloadc")
THREADS=(1 4 8 16)

RECORDCOUNT=1000000
OPCOUNT=1000000
# THREADS=16

LOG_DIR="/workspace/rocksdb/scripts/logs"
CSV="/workspace/rocksdb/scripts/figure10-big.csv"

mkdir -p $LOG_DIR

cd /workspace/YCSB
# CSV HEADER
echo "mode,workload,policy,threads,runtime_ms,throughput_ops,read_ops,avg_lat_us,min_lat_us,max_lat_us,p50_us,p95_us,p99_us" > $CSV

# =========================
# HELPERS
# =========================

REMOTE_PASS=""
REMOTE_USER="root"
REMOTE_IP="220.149.236.xx"

drop_cache() {
  echo "[INFO] Dropping Local OS cache..."
  sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

  echo "[INFO] Dropping Remote NFS Server cache..."
  # -p passes the SSH password
  # sudo -S reads the password from the piped echo
  sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_IP" \
    "echo '$REMOTE_PASS' | sudo -S sync && echo 3 | sudo -S tee /proc/sys/vm/drop_caches" > /dev/null 2>&1
}

parse_ycsb() {
    FILE=$1
    MODE=$2
    WORKLOAD=$3
    POLICY=$4
    THREADS=$5

    runtime=$(grep "\[OVERALL\], RunTime(ms)" $FILE | awk '{print $3}')
    throughput=$(grep "\[OVERALL\], Throughput" $FILE | awk '{print $3}')

    read_ops=$(grep "\[READ\], Operations" $FILE | awk '{print $3}')
    avg_lat=$(grep "\[READ\], AverageLatency" $FILE | awk '{print $3}')
    min_lat=$(grep "\[READ\], MinLatency" $FILE | awk '{print $3}')
    max_lat=$(grep "\[READ\], MaxLatency" $FILE | awk '{print $3}')
    p50=$(grep "50thPercentileLatency" $FILE | awk '{print $3}')
    p95=$(grep "95thPercentileLatency" $FILE | awk '{print $3}')
    p99=$(grep "99thPercentileLatency" $FILE | awk '{print $3}')

    echo "$MODE,$WORKLOAD,$POLICY,$THREADS,$runtime,$throughput,$read_ops,$avg_lat,$min_lat,$max_lat,$p50,$p95,$p99" >> $CSV
}

# =========================
# RUN FUNCTIONS
# =========================

run_test() {
    WORKLOAD_ORIG=$1
    DB_PATH=$2
    THREADS=$3

    WORKLOAD_NAME=$(basename "$WORKLOAD_ORIG")

    NAME="baseline"
    LOG_FILE="$LOG_DIR/${NAME}_${WORKLOAD_NAME}_${THREADS}-big.txt"

    echo "=== RUN: BASELINE ($WORKLOAD_ORIG) ==="

    drop_cache

    ./bin/ycsb run rocksdb \
        -threads $THREADS \
        -s \
        -P "$WORKLOAD_ORIG" \
        -p rocksdb.dir="$DB_PATH" \
        -p rocksdb.use_direct_reads=true \
        -p rocksdb.use_direct_io_for_flush_and_compaction=true \
        -p recordcount=$RECORDCOUNT \
        -p operationcount=$OPCOUNT \
        -p randomseed=12345 \
        -p rocksdb.statistics=true \
        > "$LOG_FILE" 2>&1

    parse_ycsb "$LOG_FILE" "baseline" "$WORKLOAD_ORIG" "none" "$THREADS"

    echo "=== DONE: BASELINE ==="
}


run_test_cachelink() {
    WORKLOAD_ORIG=$1
    DB_PATH=$2
    POLICY=$3
    THREADS=$4

    WORKLOAD_NAME=$(basename "$WORKLOAD_ORIG")

    NAME="cachelink"
    LOG_FILE="$LOG_DIR/${NAME}_${WORKLOAD_NAME}_${POLICY}_${THREADS}-big.txt"

    echo "=== RUN: CACHELINK ($WORKLOAD_ORIG, $POLICY) ==="

    drop_cache
    rm -rf /mnt/nvme/cache_file

    ./bin/ycsb run rocksdb \
        -threads $THREADS \
        -s \
        -P "$WORKLOAD_ORIG" \
        -p rocksdb.dir="$DB_PATH" \
        -p rocksdb.use_direct_reads=true \
        -p rocksdb.use_direct_io_for_flush_and_compaction=true \
        -p recordcount=$RECORDCOUNT \
        -p operationcount=$OPCOUNT \
        -p secondary_cache_uri="id=CacheLink" \
        -p cachelink="size=1073741824,eviction=$POLICY,adm_policy=random,adm_prob=1.0,file=/mnt/nvme/cache_file" \
        -p randomseed=12345 \
        -p rocksdb.statistics=true \
        > "$LOG_FILE" 2>&1

    parse_ycsb "$LOG_FILE" "cachelink" "$WORKLOAD_ORIG" "$POLICY" "$THREADS"

    echo "=== DONE: CACHELINK ($POLICY) ==="
}

# =========================
# MAIN LOOP
# =========================
for THR in "${THREADS[@]}"; do
for WORKLOAD in "${WORKLOADS[@]}"; do

    WORKLOAD_ORIG="$WORKLOAD"
    WORKLOAD_NAME=$(basename "$WORKLOAD_ORIG")

    DB_PATH="/workspace/mp1/db1m_${WORKLOAD_NAME}"

    echo "======================================"
    echo "WORKLOAD: $WORKLOAD_ORIG"
    echo "DB: $DB_PATH"
    echo "======================================"

    # LOAD (only once)
    if [ ! -d "$DB_PATH" ]; then
        echo "=== LOAD PHASE ==="

        ./bin/ycsb load rocksdb \
            -threads 16 \
            -s \
            -P "$WORKLOAD_ORIG" \
            -p rocksdb.dir="$DB_PATH" \
            -p recordcount=$RECORDCOUNT \
            -p fieldlength=4096 \
            > "$LOG_DIR/load_${WORKLOAD_NAME}.txt"

        echo "=== LOAD DONE ==="
    else
        echo "=== DB exists, skipping load ==="
    fi

    # BASELINE
    run_test "$WORKLOAD_ORIG" "$DB_PATH" "$THR"

    # CACHELINK POLICIES
    for POLICY in "${POLICIES[@]}"; do
        run_test_cachelink "$WORKLOAD_ORIG" "$DB_PATH" "$POLICY" "$THR"
    done

done
done


echo "=== ALL DONE ==="
echo "CSV saved at: $CSV"