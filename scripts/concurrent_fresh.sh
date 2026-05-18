#!/bin/bash
#
# FRESH SINGLE concurrent run (no averaging) to make Chapter 3's idle-tail
# toggle real. One isolated scratch DB, four sequential main.py calls:
#   1. gen1 concurrent, wait_for_suspend  (idle tail billed)   -> Ch3 "with idle tail"
#   2. gen1 concurrent, immediate_drop    (no idle tail)        -> Ch3 "no idle tail"
#   3. adaptive concurrent QTM=2          (idle_policy n_a, both toggle states)
#   4. adaptive concurrent QTM=8          (idle_policy n_a, both toggle states)
#
# run_id base 9000 so warehouse names (BENCHMARK_WH_..._CONCURRENT_900X) cannot
# collide with ANY prior run's names (enrich sums WAREHOUSE_METERING_HISTORY by
# name with no time window). Single run, single observation per cell, by user
# choice (noise accepted). Then settle + enrich + sentinel; the viz override
# reads this DB per idle_policy.

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
SIZES="xsmall,small,medium,large,xlarge"
DB="$ROOT/.ccfresh/benchmark_results.duckdb"
LOG="$ROOT/concurrent_fresh.log"
DONE="$ROOT/concurrent_fresh.DONE"
FAIL="$ROOT/concurrent_fresh.FAILED"
WAIT_SECONDS=10800   # 3h ACCOUNT_USAGE settle (early manual check is fine)

rm -f "$DONE" "$FAIL"
mkdir -p "$ROOT/.ccfresh"
rm -f "$DB"
: > "$LOG"
log() { echo "==== $* $(date '+%Y-%m-%d %H:%M:%S') ====" | tee -a "$LOG"; }
step() {
  local name="$1"; shift
  log "START [$name]"
  if "$@" >> "$LOG" 2>&1; then log "OK    [$name]"; return 0
  else log "FAIL  [$name] rc=$?"; return 1; fi
}

export BENCHMARK_DUCKDB_PATH="$DB"
export BENCHMARK_RUN_ID_BASE=9000

log "FRESH CONCURRENT RUN START (db=$DB base=9000 sizes=$SIZES)"

unset BENCHMARK_IMMEDIATE_DROP
step "gen1-concurrent-tail" \
  uv run main.py --warehouse-type gen1 --scenarios concurrent --sizes "$SIZES"

export BENCHMARK_IMMEDIATE_DROP=1
step "gen1-concurrent-notail" \
  uv run main.py --warehouse-type gen1 --scenarios concurrent --sizes "$SIZES"
unset BENCHMARK_IMMEDIATE_DROP

step "adaptive-concurrent-qtm2" \
  uv run main.py --warehouse-type adaptive --scenarios concurrent --qtm 2 --sizes "$SIZES"
step "adaptive-concurrent-qtm8" \
  uv run main.py --warehouse-type adaptive --scenarios concurrent --qtm 8 --sizes "$SIZES"

log "WORKLOAD DONE - settling ${WAIT_SECONDS}s for ACCOUNT_USAGE"
sleep "$WAIT_SECONDS"

step "enrich" uv run snowflake/enrich_results.py
unset BENCHMARK_DUCKDB_PATH BENCHMARK_RUN_ID_BASE

if grep -q "FAIL  \[" "$LOG"; then
  log "FRESH CONCURRENT FINISHED WITH FAILURES"; touch "$FAIL"
else
  log "FRESH CONCURRENT FINISHED CLEAN"; touch "$DONE"
fi
