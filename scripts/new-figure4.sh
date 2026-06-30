#!/bin/bash

set -e

## This is for best conf with multi L1
## Target: see which size is good 
DB_BENCH_BIN="/workspace/CacheLink/db_bench"
DB_PATH="/workspace/rocksdb_nfs/rocksdb_bench3"

NUM=3000000
VALUE_SIZE=4096
BLOCK_SIZE=16384
L1_SIZE=33554432 #32MB

CSV="scripts/new-figure4.csv"

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
# echo "Running BASELINE..."

# sync
# echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

# /workspace/rocksdb/db_bench \
#   --benchmarks=readrandom \
#   --use_existing_db=1 \
#   --duration=300 \
#   $COMMON_FLAGS \
#   > baseline_nvme.txt 2>&1

# parse_final baseline_nvme.txt "baseline_nvme" 

# -----------------------------
# FUNCTION: run cachelink on device
# -----------------------------
run_cachelink () {
  DEVICE_NAME=$1
  CACHE_PATH=$2
  EVICTION=$3
  ADM_PROB=$4
  L1_SIZE=$5

  echo "Running CacheLink on $DEVICE_NAME..."

  sync
  echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

  rm -rf $CACHE_PATH
  # mkdir -p $CACHE_PATH 1073741824 1GB

  "$DB_BENCH_BIN" \
    --benchmarks=readrandom \
    --use_existing_db=1 \
    --duration=300 \
    --cache_size=$L1_SIZE \
    --secondary_cache_uri="id=CacheLink" \
    --cachelink="size=1073741824,eviction=$EVICTION,adm_policy=random,adm_prob=$ADM_PROB,file=$CACHE_PATH" \
    $COMMON_FLAGS \
    > ${DEVICE_NAME}.txt 2>&1

  parse_final ${DEVICE_NAME}.txt "$DEVICE_NAME"
}

# ----------------------------- 
# Run for each device (L2 location)
# -----------------------------

ADM_PROBS=(1.0) 
L1_SIZES=(8388608 16777216 33554432 67108864)

SIZE=33554432
echo "Running BASELINE... $SIZE"

sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

"$DB_BENCH_BIN" \
  --benchmarks=readrandom \
  --use_existing_db=1 \
  --duration=300 \
  --cache_size=$SIZE \
  $COMMON_FLAGS \
  > baseline_figure4_$SIZE.txt 2>&1

parse_final baseline_figure4_$SIZE.txt "baseline_figure4_$SIZE" 

for SIZE in "${L1_SIZES[@]}"; do
    # echo "Running BASELINE... $SIZE"

    # sync
    # echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

    # "$DB_BENCH_BIN" \
    #   --benchmarks=readrandom \
    #   --use_existing_db=1 \
    #   --duration=300 \
    #   --cache_size=$SIZE \
    #   $COMMON_FLAGS \
    #   > baseline_nvmec_$SIZE.txt 2>&1

    # parse_final baseline_nvmec_$SIZE.txt "baseline_nvme_$SIZE" 

    for PROB in "${ADM_PROBS[@]}"; do
        run_cachelink "cachelink_nvmec_TinyLFU_$PROB.$SIZE"  "/mnt/nvme/cache_file" TinyLFU $PROB $SIZE     # NVMe ✅
    done
done
# -----------------------------
# DONE
# -----------------------------
echo "======================================"
echo "DONE. Results saved to $CSV"
echo "======================================"