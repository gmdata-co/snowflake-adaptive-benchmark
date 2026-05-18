#!/bin/bash
#
# Re-run ONLY gen1 concurrent immediate_drop (no idle tail) with the fixed
# per-size policy-aware drop. Appends to .ccfresh as a NEW run_id (base 9000,
# next free -> 9005) which supersedes the deleted buggy run 9002. gen1
# wait_for_suspend (9001) and adaptive (9003/9004) are untouched and valid.
#
# This is the ONLY bad scenario: with the old code immediate_drop got an idle
# tail anyway (warehouses dropped only at the end after auto-suspending). The
# fix drops each warehouse the instant its size finishes, so immediate_drop
# now genuinely skips the tail.

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
SIZES="xsmall,small,medium,large,xlarge"
DB="$ROOT/.ccfresh/benchmark_results.duckdb"
LOG="$ROOT/rerun_gen1_notail.log"
DONE="$ROOT/rerun_gen1_notail.DONE"
FAIL="$ROOT/rerun_gen1_notail.FAILED"
WAIT_SECONDS=10800   # 3h ACCOUNT_USAGE settle (early manual check is fine)

rm -f "$DONE" "$FAIL"
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
export BENCHMARK_IMMEDIATE_DROP=1   # no idle tail (fixed: per-size drop)

log "RE-RUN gen1 concurrent immediate_drop (fixed per-size drop) db=$DB"
step "gen1-concurrent-notail-fixed" \
  uv run main.py --warehouse-type gen1 --scenarios concurrent --sizes "$SIZES"

log "WORKLOAD DONE - settling ${WAIT_SECONDS}s for ACCOUNT_USAGE"
sleep "$WAIT_SECONDS"

unset BENCHMARK_IMMEDIATE_DROP
step "enrich" uv run snowflake/enrich_results.py
unset BENCHMARK_DUCKDB_PATH BENCHMARK_RUN_ID_BASE

if grep -q "FAIL  \[" "$LOG"; then
  log "RE-RUN FINISHED WITH FAILURES"; touch "$FAIL"
else
  log "RE-RUN FINISHED CLEAN"; touch "$DONE"
fi
