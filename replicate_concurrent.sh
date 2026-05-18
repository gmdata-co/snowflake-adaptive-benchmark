#!/bin/bash
#
# CONCURRENT-SCENARIO REPLICATION
# ===============================
# Purpose: the article's Chapter 3 conclusion ("Concurrency: Adaptive's home
# turf — wins decisively on cost") does NOT replicate in the fresh run, and
# concurrent COST is the single most variance-sensitive number in the whole
# benchmark (gen1 multi-cluster count + adaptive QTM burst). So before
# rewriting Chapter 3 we measure it N times and look at median +/- spread.
#
# Design:
#  * N independent replications, each in its OWN scratch duckdb
#    (.repcc/repK/benchmark_results.duckdb) - never touches the article DB.
#  * Reps run SERIALLY (one warehouse at a time, one rep after another) -
#    concurrency is the variable we are controlling OUT here.
#  * run_id base is namespaced per rep (repK -> base K*100) so every rep's
#    warehouse NAMES are unique. This is required: enrich's
#    WAREHOUSE_METERING_HISTORY query filters by warehouse_name with NO time
#    window, so name reuse across reps would cross-contaminate cost.
#  * gen1 = wait_for_suspend (idle tail billed) to match the article's
#    realistic cost basis. BENCHMARK_IMMEDIATE_DROP stays unset.
#  * After all reps: one 3h ACCOUNT_USAGE settle, then enrich each rep DB,
#    then aggregate (median/min/max/stdev per cell across reps).
# Stops there; Claude reads the aggregate and we rewrite Chapter 3 to reality.

cd "$(dirname "$0")"
ROOT="$(pwd)"
N=5
SIZES="xsmall,small,medium,large,xlarge"
REPDIR="$ROOT/.repcc"
LOG="$ROOT/replicate_concurrent.log"
DONE="$ROOT/replicate_concurrent.DONE"
FAIL="$ROOT/replicate_concurrent.FAILED"
WAIT_SECONDS=10800   # 3h ACCOUNT_USAGE settle

rm -f "$DONE" "$FAIL"
mkdir -p "$REPDIR"
: > "$LOG"
log() { echo "==== $* $(date '+%Y-%m-%d %H:%M:%S') ====" | tee -a "$LOG"; }

step() {
  local name="$1"; shift
  log "START [$name]"
  if "$@" >> "$LOG" 2>&1; then log "OK    [$name]"; return 0
  else log "FAIL  [$name] rc=$?"; return 1; fi
}

log "CONCURRENT REPLICATION: N=$N reps, sizes=$SIZES (serial, isolated scratch DBs)"

for i in $(seq 1 "$N"); do
  rdir="$REPDIR/rep$i"
  mkdir -p "$rdir"
  db="$rdir/benchmark_results.duckdb"
  rm -f "$db"
  export BENCHMARK_DUCKDB_PATH="$db"
  export BENCHMARK_RUN_ID_BASE=$(( i * 100 ))
  unset BENCHMARK_IMMEDIATE_DROP    # gen1 wait_for_suspend (realistic cost)

  log "REP $i/$N START (db=$db run_id_base=$BENCHMARK_RUN_ID_BASE)"
  step "rep$i-gen1-concurrent" \
    uv run main.py --warehouse-type gen1 --scenarios concurrent --sizes "$SIZES"
  step "rep$i-adaptive-concurrent-qtm2" \
    uv run main.py --warehouse-type adaptive --scenarios concurrent --qtm 2 --sizes "$SIZES"
  step "rep$i-adaptive-concurrent-qtm8" \
    uv run main.py --warehouse-type adaptive --scenarios concurrent --qtm 8 --sizes "$SIZES"
  log "REP $i/$N DONE"
done

log "ALL $N REPS FINISHED — settling ${WAIT_SECONDS}s for ACCOUNT_USAGE"
sleep "$WAIT_SECONDS"

# Enrich each rep DB independently (env points config.DUCKDB_PATH at it).
for i in $(seq 1 "$N"); do
  export BENCHMARK_DUCKDB_PATH="$REPDIR/rep$i/benchmark_results.duckdb"
  step "rep$i-enrich" uv run snowflake/enrich_results.py
done
unset BENCHMARK_DUCKDB_PATH BENCHMARK_RUN_ID_BASE

# Aggregate across all reps (median/min/max/stdev per cell).
DBS=()
for i in $(seq 1 "$N"); do DBS+=("$REPDIR/rep$i/benchmark_results.duckdb"); done
step "aggregate" uv run aggregate_concurrent.py "${DBS[@]}"

if grep -q "FAIL  \[" "$LOG"; then
  log "REPLICATION FINISHED WITH FAILURES"; touch "$FAIL"
else
  log "REPLICATION FINISHED CLEAN"; touch "$DONE"
fi
