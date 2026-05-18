#!/bin/bash
#
# 3-TRACK CONCURRENT BENCHMARK
# ===========================
# Populates the whole article (Chapters 1-4, sizes XS-XL) by running THREE
# isolated tracks at the same time:
#
#   adaptive     - CREATE ADAPTIVE WAREHOUSE; per-query billed; idle_policy=n_a
#   gen1_tail    - gen1, left to AUTO_SUSPEND before drop (idle tail billed)
#   gen1_notail  - gen1, killed the instant the workload finished (no tail)
#
# WHY THIS IS SAFE TO RUN CONCURRENTLY (it does NOT violate "fresh warehouse
# per variant"): each track uses uniquely-named warehouses and never shares or
# ALTERs one. Snowflake bills per warehouse identity, so parallel tracks on
# separate warehouses keep clean cost attribution. run_id is namespaced per
# track (adaptive 1000s / gen1_tail 2000s / gen1_notail 3000s) so names + rows
# never collide. Each track writes its OWN duckdb (DuckDB is single-writer);
# the 3 are merged afterwards into the canonical benchmark_results.duckdb.
#
# idle_policy is recorded as a REAL column at run time (BENCHMARK_IMMEDIATE_DROP
# decides gen1; adaptive is always n_a) - no post-hoc run_id guessing.
#
# Pipeline: 3 tracks (parallel) -> all done -> 3h ACCOUNT_USAGE settle ->
# merge -> enrich -> dbt build-views -> update viz JSON. Stops there ON
# PURPOSE; Claude rebuilds the viz and the user reviews/deploys. Survives
# session/SSH death (launch via nohup).

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
SIZES="xsmall,small,medium,large,xlarge"
TRACK_DIR="$ROOT/.tracks"
LOG="$ROOT/run_3track.log"
SENTINEL_DONE="$ROOT/run_3track.DONE"
SENTINEL_FAIL="$ROOT/run_3track.FAILED"
WAIT_SECONDS=10800   # 3h: WAREHOUSE_METERING_HISTORY can lag 1-3h

rm -f "$SENTINEL_DONE" "$SENTINEL_FAIL"
mkdir -p "$TRACK_DIR"
: > "$LOG"

log() { echo "==== $* $(date '+%Y-%m-%d %H:%M:%S') ====" | tee -a "$LOG"; }

# ---------------------------------------------------------------------------
# One track. Args: <name> <run_id_base> <immediate_drop:0|1> <wh_type>
# Reads the type-specific step list from stdin (one `main.py` arg-tail/line).
# Each step = one main.py invocation = one run_id (base + N). Step 1 (q1
# smoke) is FATAL for that track; steps 2+ are non-fatal so one bad scenario
# doesn't waste the whole track. Always writes a per-track sentinel.
# ---------------------------------------------------------------------------
run_track() {
  local name="$1" base="$2" immediate="$3" wtype="$4"
  local tdir="$TRACK_DIR/$name"
  local tlog="$tdir/track.log"
  local tdone="$tdir/TRACK.DONE" tfail="$tdir/TRACK.FAILED"
  mkdir -p "$tdir"
  rm -f "$tdone" "$tfail"
  : > "$tlog"

  export BENCHMARK_DUCKDB_PATH="$tdir/benchmark_results.duckdb"
  export BENCHMARK_RUN_ID_BASE="$base"
  if [ "$immediate" = "1" ]; then
    export BENCHMARK_IMMEDIATE_DROP=1
  else
    unset BENCHMARK_IMMEDIATE_DROP
  fi
  rm -f "$BENCHMARK_DUCKDB_PATH"   # fresh per-track DB

  tlog_line() { echo "==== [$name] $* $(date '+%H:%M:%S') ====" | tee -a "$tlog" >> "$LOG"; }
  tlog_line "TRACK START (wh=$wtype base=$base immediate=$immediate db=$BENCHMARK_DUCKDB_PATH)"

  local stepno=0 failed=0
  while IFS= read -r argtail; do
    [ -z "$argtail" ] && continue
    stepno=$((stepno + 1))
    tlog_line "STEP $stepno START: main.py $argtail"
    if uv run main.py $argtail >> "$tlog" 2>&1; then
      tlog_line "STEP $stepno OK"
    else
      rc=$?
      tlog_line "STEP $stepno FAIL rc=$rc"
      failed=1
      if [ "$stepno" -eq 1 ]; then
        tlog_line "ABORT TRACK: q1 smoke failed; not burning hours on this track"
        touch "$tfail"
        return 1
      fi
    fi
  done

  if [ "$failed" -eq 1 ]; then
    tlog_line "TRACK FINISHED WITH FAILURES"
    touch "$tfail"
  else
    tlog_line "TRACK FINISHED CLEAN"
    touch "$tdone"
  fi
}

# --- Launch the 3 tracks concurrently --------------------------------------
log "LAUNCHING 3 CONCURRENT TRACKS (sizes: $SIZES)"

# adaptive: QTM applies; concurrent runs at QTM2 and QTM8 (two panels).
run_track adaptive 1000 0 adaptive <<EOF &
--warehouse-type adaptive --scenarios sequential --queries 1 --sizes $SIZES
--warehouse-type adaptive --scenarios sequential --qtm 2 --sizes $SIZES --runs 3
--warehouse-type adaptive --scenarios concurrent --qtm 2 --sizes $SIZES
--warehouse-type adaptive --scenarios concurrent --qtm 8 --sizes $SIZES
--warehouse-type adaptive --scenarios dml --qtm 2 --sizes $SIZES
EOF
PID_A=$!

# gen1 wait-for-suspend (idle tail billed). gen1 concurrent is a single
# config (no QTM split).
run_track gen1_tail 2000 0 gen1 <<EOF &
--warehouse-type gen1 --scenarios sequential --queries 1 --sizes $SIZES
--warehouse-type gen1 --scenarios sequential --sizes $SIZES --runs 3
--warehouse-type gen1 --scenarios concurrent --sizes $SIZES
--warehouse-type gen1 --scenarios dml --sizes $SIZES
EOF
PID_T=$!

# gen1 immediate-drop (no idle tail) - same matrix, BENCHMARK_IMMEDIATE_DROP=1.
run_track gen1_notail 3000 1 gen1 <<EOF &
--warehouse-type gen1 --scenarios sequential --queries 1 --sizes $SIZES
--warehouse-type gen1 --scenarios sequential --sizes $SIZES --runs 3
--warehouse-type gen1 --scenarios concurrent --sizes $SIZES
--warehouse-type gen1 --scenarios dml --sizes $SIZES
EOF
PID_N=$!

log "Track PIDs: adaptive=$PID_A gen1_tail=$PID_T gen1_notail=$PID_N"
wait "$PID_A" "$PID_T" "$PID_N"
log "ALL 3 TRACKS FINISHED"
for t in adaptive gen1_tail gen1_notail; do
  if [ -f "$TRACK_DIR/$t/TRACK.DONE" ]; then s=CLEAN; else s=FAILED; fi
  log "  track $t: $s"
done

# --- Settle + merge + enrich + transform + refresh viz JSON ----------------
log "SETTLE: sleeping ${WAIT_SECONDS}s for ACCOUNT_USAGE to populate"
sleep "$WAIT_SECONDS"

step() {
  local name="$1"; shift
  log "START [$name]"
  if "$@" >> "$LOG" 2>&1; then log "OK    [$name]"; return 0
  else log "FAIL  [$name] rc=$?"; return 1; fi
}

step "merge" uv run merge_tracks.py \
  "$TRACK_DIR/adaptive/benchmark_results.duckdb" \
  "$TRACK_DIR/gen1_tail/benchmark_results.duckdb" \
  "$TRACK_DIR/gen1_notail/benchmark_results.duckdb"

# enrich / dbt / viz must hit the CANONICAL db -> env unset.
unset BENCHMARK_DUCKDB_PATH BENCHMARK_RUN_ID_BASE BENCHMARK_IMMEDIATE_DROP
step "enrich"      uv run snowflake/enrich_results.py
step "build-views" bash common/transformations/build_views.sh
step "update-viz"  uv run visualization/update_data.py

# Intentionally NO viz rebuild/redeploy - Claude rebuilds, user reviews.
if grep -q "FAIL  \[" "$LOG" || ls "$TRACK_DIR"/*/TRACK.FAILED >/dev/null 2>&1; then
  log "PIPELINE FINISHED WITH FAILURES"
  touch "$SENTINEL_FAIL"
else
  log "PIPELINE FINISHED CLEAN"
  touch "$SENTINEL_DONE"
fi
