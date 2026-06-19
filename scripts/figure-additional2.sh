#!/bin/bash

set -e

## Target: causal metrics for No-sec vs CacheLink-NVMe only

DB_PATH="/workspace/mp3/rocksdb_bench3"

NUM=3000000
VALUE_SIZE=4096
BLOCK_SIZE=16384
L1_SIZE=33554432 # 32MB

OUTPUT_DIR="scripts" 
mkdir -p "$OUTPUT_DIR"

METRICS_CSV="$OUTPUT_DIR/metrics_no_sec_vs_cachelink_nvme_hit2.csv"

echo "mode,qps,latency_us,seconds,operations,mbps,block_hit,block_miss,secondary_hits,secondary_hit_ratio,backend_miss_est,cache_file_bytes" > "$METRICS_CSV"

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

parse_intervals () {
  FILE=$1
  OUT_CSV=$2

  TIME=0
  echo "time,qps,latency_us" > "$OUT_CSV"

  grep -E "ops/sec|ops/second" "$FILE" | while read -r line; do
    QPS=$(echo "$line" | grep -oP '[0-9.]+(?= ops/sec| ops/second)' | head -1)
    LAT=$(echo "$line" | grep -oP '[0-9.]+(?= micros/op)' | head -1)

    if [[ -n "$QPS" && -n "$LAT" ]]; then
      echo "$TIME,$QPS,$LAT" >> "$OUT_CSV"
      TIME=$((TIME+1))
    fi
  done
}

parse_metrics () {
  MODE=$1
  OUT_TXT=$2
  CACHE_PATH=$3

  LINE=$(grep "^readrandom" "$OUT_TXT" | tail -1)

  LAT=$(echo "$LINE" | grep -oP '[0-9.]+(?= micros/op)' | head -1)
  QPS=$(echo "$LINE" | grep -oP '[0-9]+(?= ops/sec)' | head -1)
  SECONDS=$(echo "$LINE" | grep -oP '[0-9.]+(?= seconds)' | head -1)
  OPS=$(echo "$LINE" | grep -oP '[0-9]+(?= operations)' | head -1)
  MBPS=$(echo "$LINE" | grep -oP '[0-9.]+(?= MB/s)' | head -1)

  BLOCK_HIT=$(grep "rocksdb.block.cache.hit COUNT" "$OUT_TXT" | tail -1 | grep -oP '[0-9]+' | tail -1)
  BLOCK_MISS=$(grep "rocksdb.block.cache.miss COUNT" "$OUT_TXT" | tail -1 | grep -oP '[0-9]+' | tail -1)
  SECONDARY_HITS=$(grep "rocksdb.secondary.cache.hits COUNT" "$OUT_TXT" | tail -1 | grep -oP '[0-9]+' | tail -1)

  BLOCK_HIT=${BLOCK_HIT:-0}
  BLOCK_MISS=${BLOCK_MISS:-0}
  SECONDARY_HITS=${SECONDARY_HITS:-0}

  if [[ "$BLOCK_MISS" -gt 0 ]]; then
    SECONDARY_HIT_RATIO=$(awk -v h="$SECONDARY_HITS" -v m="$BLOCK_MISS" 'BEGIN { printf "%.4f", h/m }')
    BACKEND_MISS_EST=$(awk -v h="$SECONDARY_HITS" -v m="$BLOCK_MISS" 'BEGIN { x=m-h; if (x<0) x=0; printf "%.0f", x }')
  else
    SECONDARY_HIT_RATIO="0"
    BACKEND_MISS_EST="0"
  fi

  if [[ -n "$CACHE_PATH" && -f "$CACHE_PATH" ]]; then
    CACHE_FILE_BYTES=$(stat -c%s "$CACHE_PATH")
  else
    CACHE_FILE_BYTES=0
  fi

  echo "$MODE,$QPS,$LAT,$SECONDS,$OPS,$MBPS,$BLOCK_HIT,$BLOCK_MISS,$SECONDARY_HITS,$SECONDARY_HIT_RATIO,$BACKEND_MISS_EST,$CACHE_FILE_BYTES" >> "$METRICS_CSV"

  grep -E "readrandom|rocksdb.block.cache.hit|rocksdb.block.cache.miss|rocksdb.secondary.cache.hits" "$OUT_TXT" \
    > "$OUTPUT_DIR/summary_${MODE}.txt" || true
}

run_one () {
  MODE=$1
  CACHE_PATH=$2
  EXTRA_FLAGS=$3

  echo "Running $MODE..."

  sync
  echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

  if [[ -n "$CACHE_PATH" ]]; then
    rm -rf "$CACHE_PATH"
  fi

  OUT_TXT="$OUTPUT_DIR/${MODE}.txt"
  OUT_CSV="$OUTPUT_DIR/${MODE}_timeseries.csv"

  /workspace/rocksdb/db_bench \
    --benchmarks=readrandom \
    --use_existing_db=1 \
    --reads=1000000 \
    $EXTRA_FLAGS \
    $COMMON_FLAGS \
    > "$OUT_TXT" 2>&1

  parse_intervals "$OUT_TXT" "$OUT_CSV"
  parse_metrics "$MODE" "$OUT_TXT" "$CACHE_PATH"
}

# -----------------------------
# Baseline: No secondary cache
# -----------------------------
run_one "baseline_no_secondary_cache_hit2" "" ""

# -----------------------------
# CacheLink: NVMe only
# -----------------------------
NVME_CACHE_PATH="/mnt/nvme/cache_file"

CACHELINK_NVME_FLAGS="\
  --secondary_cache_uri=id=CacheLink \
  --cachelink=size=1073741824,eviction=TinyLFU,adm_policy=random,adm_prob=1.0,file=$NVME_CACHE_PATH"

run_one "cachelink_nvme_TinyLFU_1.0_hit2" "$NVME_CACHE_PATH" "$CACHELINK_NVME_FLAGS"

echo "======================================"
echo "DONE."
echo "Metrics: $METRICS_CSV"
echo "Time series: $OUTPUT_DIR/*_timeseries.csv"
echo "Summaries: $OUTPUT_DIR/summary_*.txt"
echo "======================================"