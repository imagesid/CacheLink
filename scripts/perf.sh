#!/bin/bash

set -e

# ============================================================
# Perf CPU profiling for RocksDB db_bench
# Compare baseline RocksDB vs CacheLink
# ============================================================

DB_PATH="/workspace/mp1/rocksdb_bench"

NUM=3000000
VALUE_SIZE=4096
BLOCK_SIZE=16384
L1_SIZE=33554432 # 32MB

# perf stat can run longer for stable hardware counters
DURATION_STAT=300

# perf record should be shorter because call-graph profiling is expensive
DURATION_RECORD=60

# Sampling frequency for perf record
PERF_RECORD_FREQ=49

# Set to 1 only if you rebuilt db_bench with debug symbols/frame pointers
# DWARF is slower but can give deeper call stacks.
USE_DWARF=0

CACHE_SIZE=1073741824 # 1GB
CACHE_PATH="/mnt/nvme/cache_file"
EVICTION="TinyLFU"
ADM_PROB="1.0"

ROCKSDB_BENCH="/workspace/rocksdb/db_bench"

OUT_DIR="scripts/perf_cpu_profile"
mkdir -p "$OUT_DIR"

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

PERF_EVENTS="\
cycles,instructions,branches,branch-misses,cache-references,cache-misses,\
context-switches,cpu-migrations,page-faults,task-clock,cpu-clock"

# ============================================================
# Check tools
# ============================================================

if ! command -v perf >/dev/null 2>&1; then
  echo "ERROR: perf is not installed."
  echo "Install with: sudo apt update && sudo apt install -y linux-tools-common linux-tools-generic"
  exit 1
fi

if [[ ! -x "$ROCKSDB_BENCH" ]]; then
  echo "ERROR: db_bench not found or not executable: $ROCKSDB_BENCH"
  exit 1
fi

# ============================================================
# Helper: drop cache
# ============================================================

drop_cache() {
  sync
  echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
}

# ============================================================
# Helper: parse final db_bench result
# ============================================================

parse_final() {
  FILE=$1
  MODE=$2
  CSV=$3
  RUN_TYPE=$4

  LINE=$(grep "^readrandom" "$FILE" | tail -1 || true)

  LAT=$(echo "$LINE" | grep -oP '[0-9.]+(?= micros/op)' || true)
  QPS=$(echo "$LINE" | grep -oP '[0-9]+(?= ops/sec)' || true)
  SECONDS=$(echo "$LINE" | grep -oP '[0-9.]+(?= seconds)' || true)
  OPS=$(echo "$LINE" | grep -oP '[0-9]+(?= operations)' || true)
  MBPS=$(echo "$LINE" | grep -oP '[0-9.]+(?= MB/s)' || true)

  if [[ -z "$LAT" || -z "$QPS" ]]; then
    echo "WARNING: Failed to parse db_bench final line for $MODE ($RUN_TYPE)"
    echo "$LINE"
    LAT="NA"
    QPS="NA"
    SECONDS="NA"
    OPS="NA"
    MBPS="NA"
  fi

  echo "$MODE,$RUN_TYPE,$LAT,$QPS,$SECONDS,$OPS,$MBPS" >> "$CSV"
}

# ============================================================
# Run perf stat
# ============================================================

run_perf_stat() {
  MODE=$1
  EXTRA_FLAGS=$2

  echo "======================================"
  echo "Running perf stat: $MODE"
  echo "Duration: ${DURATION_STAT}s"
  echo "======================================"

  drop_cache

  DBBENCH_OUT="$OUT_DIR/${MODE}_stat_dbbench.txt"
  PERF_STAT_OUT="$OUT_DIR/${MODE}_perf_stat.txt"

  if [[ "$MODE" == cachelink* ]]; then
    rm -f "$CACHE_PATH"
  fi

  perf stat \
    -e "$PERF_EVENTS" \
    -o "$PERF_STAT_OUT" \
    -- \
    "$ROCKSDB_BENCH" \
      --benchmarks=readrandom \
      --use_existing_db=1 \
      --duration=$DURATION_STAT \
      $EXTRA_FLAGS \
      $COMMON_FLAGS \
      > "$DBBENCH_OUT" 2>&1

  parse_final "$DBBENCH_OUT" "$MODE" "$OUT_DIR/dbbench_summary.csv" "perf_stat"

  echo "Saved:"
  echo "  $DBBENCH_OUT"
  echo "  $PERF_STAT_OUT"
}

# ============================================================
# Run perf record for function-level profile
# ============================================================

run_perf_record() {
  MODE=$1
  EXTRA_FLAGS=$2

  echo "======================================"
  echo "Running perf record: $MODE"
  echo "Duration: ${DURATION_RECORD}s"
  echo "Frequency: ${PERF_RECORD_FREQ} Hz"
  echo "USE_DWARF: ${USE_DWARF}"
  echo "======================================"

  drop_cache

  DBBENCH_OUT="$OUT_DIR/${MODE}_record_dbbench.txt"
  PERF_DATA="$OUT_DIR/${MODE}.perf.data"
  PERF_REPORT="$OUT_DIR/${MODE}_perf_report.txt"
  PERF_REPORT_CHILDREN="$OUT_DIR/${MODE}_perf_report_children.txt"
  PERF_SCRIPT="$OUT_DIR/${MODE}_perf_script.txt"

  if [[ "$MODE" == cachelink* ]]; then
    rm -f "$CACHE_PATH"
  fi

  if [[ "$USE_DWARF" == "1" ]]; then
    CALLGRAPH_FLAGS="-g --call-graph dwarf"
  else
    CALLGRAPH_FLAGS="-g"
  fi

  perf record \
    -F "$PERF_RECORD_FREQ" \
    $CALLGRAPH_FLAGS \
    -o "$PERF_DATA" \
    -- \
    "$ROCKSDB_BENCH" \
      --benchmarks=readrandom \
      --use_existing_db=1 \
      --duration=$DURATION_RECORD \
      $EXTRA_FLAGS \
      $COMMON_FLAGS \
      > "$DBBENCH_OUT" 2>&1

  parse_final "$DBBENCH_OUT" "$MODE" "$OUT_DIR/dbbench_summary.csv" "perf_record"

  # Function-level flat report: direct CPU cost per symbol
  perf report \
    -i "$PERF_DATA" \
    --stdio \
    --no-children \
    --sort comm,dso,symbol \
    > "$PERF_REPORT"

  # Inclusive report: parent/call-path contribution
  perf report \
    -i "$PERF_DATA" \
    --stdio \
    --children \
    --sort comm,dso,symbol \
    > "$PERF_REPORT_CHILDREN"

  # Raw script output, useful for FlameGraph later
  perf script \
    -i "$PERF_DATA" \
    > "$PERF_SCRIPT" || true

  echo "Saved:"
  echo "  $DBBENCH_OUT"
  echo "  $PERF_DATA"
  echo "  $PERF_REPORT"
  echo "  $PERF_REPORT_CHILDREN"
  echo "  $PERF_SCRIPT"
}

# ============================================================
# Create summary CSV
# ============================================================

echo "mode,run_type,latency_us,qps,seconds,operations,mbps" > "$OUT_DIR/dbbench_summary.csv"

# ============================================================
# Configurations
# ============================================================

BASELINE_FLAGS=""

CACHELINK_FLAGS="\
  --secondary_cache_uri=id=CacheLink \
  --cachelink=size=$CACHE_SIZE,eviction=$EVICTION,adm_policy=random,adm_prob=$ADM_PROB,file=$CACHE_PATH"

# ============================================================
# Main runs
# ============================================================

run_perf_stat "baseline" "$BASELINE_FLAGS"
run_perf_stat "cachelink_nvme_${EVICTION}_${ADM_PROB}" "$CACHELINK_FLAGS"

run_perf_record "baseline" "$BASELINE_FLAGS"
run_perf_record "cachelink_nvme_${EVICTION}_${ADM_PROB}" "$CACHELINK_FLAGS"

# ============================================================
# Print top functions
# ============================================================

echo "======================================"
echo "Top baseline CPU functions"
echo "======================================"
grep -E "^[[:space:]]+[0-9]+\.[0-9]+%" "$OUT_DIR/baseline_perf_report.txt" | head -30 || true

echo "======================================"
echo "Top CacheLink CPU functions"
echo "======================================"
grep -E "^[[:space:]]+[0-9]+\.[0-9]+%" "$OUT_DIR/cachelink_nvme_${EVICTION}_${ADM_PROB}_perf_report.txt" | head -30 || true

echo "======================================"
echo "Top CacheLink inclusive call paths"
echo "======================================"
grep -E "^[[:space:]]+[0-9]+\.[0-9]+%" "$OUT_DIR/cachelink_nvme_${EVICTION}_${ADM_PROB}_perf_report_children.txt" | head -30 || true

echo "======================================"
echo "Generated files:"
echo "======================================"
echo "$OUT_DIR/dbbench_summary.csv"
echo "$OUT_DIR/baseline_perf_stat.txt"
echo "$OUT_DIR/cachelink_nvme_${EVICTION}_${ADM_PROB}_perf_stat.txt"
echo "$OUT_DIR/baseline_perf_report.txt"
echo "$OUT_DIR/cachelink_nvme_${EVICTION}_${ADM_PROB}_perf_report.txt"
echo "$OUT_DIR/baseline_perf_report_children.txt"
echo "$OUT_DIR/cachelink_nvme_${EVICTION}_${ADM_PROB}_perf_report_children.txt"
echo "$OUT_DIR/baseline_perf_script.txt"
echo "$OUT_DIR/cachelink_nvme_${EVICTION}_${ADM_PROB}_perf_script.txt"
echo "======================================"
echo "DONE"
echo "======================================"