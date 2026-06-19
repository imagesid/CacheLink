#!/bin/bash

set -e

## CPU overhead experiment for CacheLink 
## Target: compare CPU usage between baseline RocksDB and CacheLink 

DB_PATH="/workspace/mp1/rocksdb_bench"

NUM=3000000
VALUE_SIZE=4096
BLOCK_SIZE=16384
L1_SIZE=33554432 # 32MB
DURATION=300

CACHE_SIZE=1073741824 # 1GB
CACHE_PATH="/mnt/nvme/cache_file"
EVICTION="TinyLFU"
ADM_PROB="1.0"

CSV="scripts/cpu_overhead_dbbench.csv"
LOG_DIR="scripts/cpu_overhead_logs"

mkdir -p "$LOG_DIR"

echo "mode,latency_us,qps,seconds,operations,mbps,cpu_user_pct,cpu_system_pct,cpu_wait_pct,cpu_total_pct,cpu_time_per_op_us,rss_kb,mem_pct" > "$CSV"

FILL_COMMON_FLAGS="\
  --db=$DB_PATH \
  --num=$NUM \
  --value_size=$VALUE_SIZE \
  --block_size=$BLOCK_SIZE \
  --cache_size=$L1_SIZE \
  --use_direct_reads=1 \
  --use_direct_io_for_flush_and_compaction=1 \
  --compression_type=none \
  --statistics \
  --seed=12345"

COMMON_FLAGS="\
  --db=$DB_PATH \
  --num=$NUM \
  --value_size=$VALUE_SIZE \
  --block_size=$BLOCK_SIZE \
  --cache_size=$L1_SIZE \
  --use_direct_reads=1 \
  --use_direct_io_for_flush_and_compaction=1 \
  --compression_type=none \
  --statistics \
  --stats_interval_seconds=1 \
  --stats_per_interval=1 \
  --seed=12345"

# -----------------------------
# FUNCTION: parse FINAL db_bench result
# -----------------------------
parse_final () {
  FILE=$1

  LINE=$(grep "^readrandom" "$FILE" | tail -1)

  LAT=$(echo "$LINE" | grep -oP '[0-9.]+(?= micros/op)' || true)
  QPS=$(echo "$LINE" | grep -oP '[0-9]+(?= ops/sec)' || true)
  SECONDS=$(echo "$LINE" | grep -oP '[0-9.]+(?= seconds)' || true)
  OPS=$(echo "$LINE" | grep -oP '[0-9]+(?= operations)' || true)
  MBPS=$(echo "$LINE" | grep -oP '[0-9.]+(?= MB/s)' || true)

  if [[ -z "$LAT" || -z "$QPS" ]]; then
    echo "WARNING: Failed to parse db_bench result from $FILE"
    echo "$LINE"
    LAT="NA"
    QPS="NA"
    SECONDS="NA"
    OPS="NA"
    MBPS="NA"
  fi
}

# -----------------------------
# FUNCTION: parse pidstat CPU result
# -----------------------------
parse_pidstat_cpu () {
  FILE=$1

  # pidstat -u average format:
  # Average: UID PID %usr %system %guest %wait %CPU CPU Command
  CPU_LINE=$(grep "^Average:" "$FILE" | grep "db_bench" | tail -1 || true)

  if [[ -n "$CPU_LINE" ]]; then
    CPU_USER=$(echo "$CPU_LINE" | awk '{print $4}')
    CPU_SYSTEM=$(echo "$CPU_LINE" | awk '{print $5}')
    CPU_WAIT=$(echo "$CPU_LINE" | awk '{print $7}')
    CPU_TOTAL=$(echo "$CPU_LINE" | awk '{print $8}')
  else
    echo "WARNING: Failed to parse CPU pidstat from $FILE"
    CPU_USER="NA"
    CPU_SYSTEM="NA"
    CPU_WAIT="NA"
    CPU_TOTAL="NA"
  fi
}

# -----------------------------
# FUNCTION: parse pidstat memory result
# -----------------------------
parse_pidstat_mem () {
  FILE=$1

  # pidstat -r average format:
  # Average: UID PID minflt/s majflt/s VSZ RSS %MEM Command
  MEM_LINE=$(grep "^Average:" "$FILE" | grep "db_bench" | tail -1 || true)

  if [[ -n "$MEM_LINE" ]]; then
    RSS_KB=$(echo "$MEM_LINE" | awk '{print $7}')
    MEM_PCT=$(echo "$MEM_LINE" | awk '{print $8}')
  else
    echo "WARNING: Failed to parse MEM pidstat from $FILE"
    RSS_KB="NA"
    MEM_PCT="NA"
  fi
}

# -----------------------------
# FUNCTION: calculate CPU time per operation
# -----------------------------
calc_cpu_time_per_op () {
  if [[ "$CPU_TOTAL" != "NA" && "$SECONDS" != "NA" && "$OPS" != "NA" && "$OPS" != "0" ]]; then
    CPU_TIME_PER_OP_US=$(awk -v cpu="$CPU_TOTAL" -v sec="$SECONDS" -v ops="$OPS" \
      'BEGIN { printf "%.4f", ((cpu / 100.0) * sec * 1000000.0) / ops }')
  else
    CPU_TIME_PER_OP_US="NA"
  fi
}

# -----------------------------
# FUNCTION: run db_bench with pidstat
# -----------------------------
run_with_pidstat () {
  MODE=$1
  EXTRA_FLAGS=$2

  OUT_FILE="$LOG_DIR/${MODE}_pidstat.txt" 
  CPU_FILE="$LOG_DIR/${MODE}_pidstat_cpu.txt"
  MEM_FILE="$LOG_DIR/${MODE}_pidstat_mem.txt"

  echo "======================================"
  echo "Running $MODE"
  echo "======================================"

  sync
  echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

  /workspace/rocksdb/db_bench \
    --benchmarks=readrandom \
    --use_existing_db=1 \
    --duration=$DURATION \
    $EXTRA_FLAGS \
    $COMMON_FLAGS \
    > "$OUT_FILE" 2>&1 &

  BENCH_PID=$!

  echo "db_bench PID: $BENCH_PID"

  # Start pidstat monitors
  pidstat -u -p "$BENCH_PID" 1 > "$CPU_FILE" 2>&1 &
  CPU_MON_PID=$!

  pidstat -r -p "$BENCH_PID" 1 > "$MEM_FILE" 2>&1 &
  MEM_MON_PID=$!

  # Wait for db_bench to finish
  wait "$BENCH_PID"

  # Give pidstat a moment, then stop it with SIGINT so it prints Average line
  sleep 2
  kill -INT "$CPU_MON_PID" 2>/dev/null || true
  kill -INT "$MEM_MON_PID" 2>/dev/null || true

  sleep 1

  parse_final "$OUT_FILE"
  parse_pidstat_cpu "$CPU_FILE"
  parse_pidstat_mem "$MEM_FILE"
  calc_cpu_time_per_op

  echo "$MODE,$LAT,$QPS,$SECONDS,$OPS,$MBPS,$CPU_USER,$CPU_SYSTEM,$CPU_WAIT,$CPU_TOTAL,$CPU_TIME_PER_OP_US,$RSS_KB,$MEM_PCT" >> "$CSV"

  echo "Finished $MODE"
  echo "QPS=$QPS latency_us=$LAT CPU=$CPU_TOTAL% CPU_time_per_op_us=$CPU_TIME_PER_OP_US RSS=${RSS_KB}KB"
}

# -----------------------------
# Fill DB only once if needed
# -----------------------------
# echo "Filling DB..."
# rm -rf "$DB_PATH"
#
# /workspace/rocksdb/db_bench \
#   --benchmarks=fillrandom \
#   $FILL_COMMON_FLAGS > "$LOG_DIR/fillrandom.txt" 2>&1

# -----------------------------
# BASELINE
# -----------------------------
run_with_pidstat "baseline" ""

# -----------------------------
# CACHELINK: NVMe + TinyLFU + admission 1.0
# -----------------------------
rm -f "$CACHE_PATH"

CACHELINK_FLAGS="\
  --secondary_cache_uri=id=CacheLink \
  --cachelink=size=$CACHE_SIZE,eviction=$EVICTION,adm_policy=random,adm_prob=$ADM_PROB,file=$CACHE_PATH"

run_with_pidstat "cachelink_nvme_${EVICTION}_${ADM_PROB}" "$CACHELINK_FLAGS"

# -----------------------------
# DONE
# -----------------------------
echo "======================================"
echo "DONE. Results saved to $CSV"
echo "Logs saved to $LOG_DIR"
echo "======================================"