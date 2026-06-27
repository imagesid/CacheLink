#!/bin/bash

set -e

## Target: compare device performance using time series

DB_PATH="/workspace/mp3/rocksdb_bench3"

NUM=3000000
VALUE_SIZE=4096
BLOCK_SIZE=16384
L1_SIZE=33554432 # 32MB

OUTPUT_DIR="scripts"
mkdir -p $OUTPUT_DIR

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
# FUNCTION: extract time series → separate CSV
# -----------------------------
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

# -----------------------------
# BASELINE (NO L2)
# -----------------------------
echo "Running BASELINE..."

sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

BASE_TXT="$OUTPUT_DIR/baseline_nvme_tsb.txt"
BASE_CSV="$OUTPUT_DIR/baseline_nvme_tsb.csv"

/workspace/rocksdb/db_bench \
  --benchmarks=readrandom \
  --use_existing_db=1 \
  --duration=3600 \
  $COMMON_FLAGS \
  > $BASE_TXT 2>&1

parse_intervals "$BASE_TXT" "$BASE_CSV"

# -----------------------------
# FUNCTION: run cachelink
# -----------------------------
run_cachelink () {
  DEVICE_NAME=$1
  CACHE_PATH=$2
  EVICTION=$3
  ADM_PROB=$4

  echo "Running $DEVICE_NAME..."

  sync
  echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

  rm -rf $CACHE_PATH

  OUT_TXT="$OUTPUT_DIR/${DEVICE_NAME}_tsb.txt"
  OUT_CSV="$OUTPUT_DIR/${DEVICE_NAME}_tsb.csv"

  /workspace/rocksdb/db_bench \
    --benchmarks=readrandom \
    --use_existing_db=1 \
    --duration=3600 \
    --secondary_cache_uri="id=CacheLink" \
    --cachelink="size=1073741824,eviction=$EVICTION,adm_policy=random,adm_prob=$ADM_PROB,file=$CACHE_PATH" \
    $COMMON_FLAGS \
    > $OUT_TXT 2>&1

  parse_intervals "$OUT_TXT" "$OUT_CSV"
}

# -----------------------------
# RUN EXPERIMENTS
# -----------------------------
ADM_PROBS=(1.0)

DEVICES=(
  "/mnt/hdd2/cache_file"
  "/workspace/CacheLink/cache_file"
  "/mnt/hdd1/cache_file"
  "/mnt/nvme/cache_file"
)

DEVICE_NAMES=(
  "hdd"
  "ssd1"
  "ssd2"
  "nvme"
)

for i in "${!DEVICES[@]}"; do
  DEVICE=${DEVICES[$i]}
  NAME=${DEVICE_NAMES[$i]}

  for PROB in "${ADM_PROBS[@]}"; do
    run_cachelink "cachelink_${NAME}_TinyLFU_${PROB}" "$DEVICE" TinyLFU $PROB
  done
done

# -----------------------------
# DONE
# -----------------------------
echo "======================================"
echo "DONE. Time series CSV saved in $OUTPUT_DIR"
echo "======================================"