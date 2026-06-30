#!/bin/bash

set -e


## Target: what device is the fastest
DB_BENCH_BIN="/workspace/CacheLink/db_bench"
DB_PATH="/workspace/rocksdb_nfs/rocksdb_bench3" 

NUM=3000000
VALUE_SIZE=4096
BLOCK_SIZE=16384
L1_SIZE=33554432 #32MB

CSV="scripts/new-figure2.csv" 

# echo "time,mode,qps,latency_us" > $CSV
echo "mode,latency_us,qps,seconds,operations,mbps" > $CSV

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
# FUNCTION: extract interval stats
# -----------------------------
parse_intervals () {
  FILE=$1
  MODE=$2

  TIME=0

  grep "ops/sec" "$FILE" | while read -r line; do
    QPS=$(echo "$line" | grep -oP '[0-9]+(?= ops/sec)' | head -1)
    LAT=$(echo "$line" | grep -oP '[0-9.]+(?= micros/op)' | head -1)

    if [[ -n "$QPS" && -n "$LAT" ]]; then
      echo "$TIME,$MODE,$QPS,$LAT" >> $CSV
      TIME=$((TIME+1))
    fi
  done
}

# -----------------------------
# FUNCTION: extract FINAL result
# -----------------------------
parse_final () {
  FILE=$1
  MODE=$2

  LINE=$(grep "^readrandom" "$FILE" | tail -1)

  LAT=$(echo "$LINE" | grep -oP '[0-9.]+(?= micros/op)')
  QPS=$(echo "$LINE" | grep -oP '[0-9]+(?= ops/sec)')
  DURATION=$(echo "$LINE" | grep -oP '[0-9.]+(?= seconds)')
  OPS=$(echo "$LINE" | grep -oP '[0-9]+(?= operations)')
  MBPS=$(echo "$LINE" | grep -oP '[0-9.]+(?= MB/s)')

  if [[ -n "$LAT" && -n "$QPS" ]]; then
    echo "$MODE,$LAT,$QPS,$DURATION,$OPS,$MBPS" >> $CSV
  else
    echo "WARNING: Failed to parse $FILE"
    echo "$LINE"
  fi
}

# -----------------------------
# BASELINE (NO L2)
# -----------------------------
echo "Running BASELINE..."

sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

# nfsstat -c > nfs_before.txt

"$DB_BENCH_BIN" \
  --benchmarks=readrandom \
  --use_existing_db=1 \
  --duration=300 \
  $COMMON_FLAGS \
  > baseline_figure2.txt 2>&1

parse_final baseline_figure2.txt "baseline_figure2" 



run_rocksdb_sec () {
  DEVICE_NAME=$1
#   CACHE_PATH=$2
#   EVICTION=$3
#   ADM_PROB=$4

  echo "Running rocksdb sec on $DEVICE_NAME..."

  sync
  echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

  rm -rf $CACHE_PATH
  # mkdir -p $CACHE_PATH

  "$DB_BENCH_BIN" \
    --benchmarks=readrandom \
    --use_existing_db=1 \
    --duration=300 \
    --use_compressed_secondary_cache=true \
    --compressed_secondary_cache_size=1073741824 \
    $COMMON_FLAGS \
    > ${DEVICE_NAME}.txt 2>&1

  parse_final ${DEVICE_NAME}.txt "$DEVICE_NAME"
}

run_rocksdb_sec "rocksdb-sec"

run_cachelink () {
  DEVICE_NAME=$1
  CACHE_PATH=$2
  EVICTION=$3
  ADM_PROB=$4

  echo "Running CacheLink on $DEVICE_NAME..."

  sync
  echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

  rm -rf $CACHE_PATH
  # mkdir -p $CACHE_PATH

  "$DB_BENCH_BIN" \
    --benchmarks=readrandom \
    --use_existing_db=1 \
    --duration=300 \
    --secondary_cache_uri="id=CacheLink" \
    --cachelink="size=1073741824,eviction=$EVICTION,adm_policy=random,adm_prob=$ADM_PROB,file=$CACHE_PATH" \
    $COMMON_FLAGS \
    > ${DEVICE_NAME}.txt 2>&1

  parse_final ${DEVICE_NAME}.txt "$DEVICE_NAME"
}


ADM_PROBS=(1.0)

DEVICE_NAMES=("hdd" "workspace_ssd" "ssd" "nvme")
DEVICE_PATHS=(
  "/mnt/hdd/cache_file"
  "/workspace/CacheLink/cache_file"
  "/mnt/ssd/cache_file"
  "/mnt/nvme/cache_file"
)

for i in "${!DEVICE_PATHS[@]}"; do
  DEVICE_NAME="${DEVICE_NAMES[$i]}"
  DEVICE="${DEVICE_PATHS[$i]}"

  for PROB in "${ADM_PROBS[@]}"; do
    run_cachelink "cachelink_${DEVICE_NAME}_LRU_${PROB}.device" "$DEVICE" LRU "$PROB"
  done
done
# -----------------------------
# DONE
# -----------------------------
echo "======================================"
echo "DONE. Results saved to $CSV"
echo "======================================"