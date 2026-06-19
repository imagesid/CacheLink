#!/bin/bash

set -e

DB_PATH="/export/rocksdb_data/rocksdb_bench3"

NUM=3000000
VALUE_SIZE=4096
BLOCK_SIZE=16384
L1_SIZE=33554432

CSV="latency_timeseries_devices.csv"

echo "time,mode,qps,latency_us" > $CSV

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
# Fill DB (only once)
# -----------------------------
echo "Filling DB..."
rm -rf $DB_PATH

./db_bench \
  --benchmarks=fillrandom \
  $FILL_COMMON_FLAGS > /dev/null
