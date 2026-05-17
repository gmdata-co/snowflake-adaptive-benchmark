#!/bin/bash
# Overnight orchestrator:
#   1. wait for the in-flight run 009 (immediate-drop baseline) to finish
#   2. run the full sequential 3x again with NEW behaviour: gen1 AUTO_SUSPEND=60
#      and cleanup waits for the warehouse to actually SUSPEND before DROP,
#      so the idle billing tail lands in WAREHOUSE_METERING_HISTORY
#   3. let ACCOUNT_USAGE settle, enrich, rebuild dbt views, refresh chart JSON
# Stops there ON PURPOSE: the article body must be rewritten for the new data
# story before anything is republished to the customer site. Survives session
# crashes (launched via nohup). Writes a sentinel at the end so a watcher can
# notify Claude on TRUE completion to do the rewrite + redeploy.
cd "$(dirname "$0")"
LOG=overnight.log
SENTINEL_DONE=overnight.DONE
SENTINEL_FAIL=overnight.FAILED
rm -f "$SENTINEL_DONE" "$SENTINEL_FAIL"
: > "$LOG"

log() { echo "==== $* $(date '+%Y-%m-%d %H:%M:%S') ====" | tee -a "$LOG"; }

# --- 1. Wait for run 009 to finish -----------------------------------------
log "STEP 1: waiting for in-flight run 009 (pid 299158) to finish"
while kill -0 299158 2>/dev/null; do sleep 60; done
log "STEP 1 DONE: run 009 process exited"
sleep 20  # let final DuckDB writes flush

# --- 2. Run 010 with wait-until-suspended drop behaviour --------------------
log "STEP 2: launching run 010 (gen1 60s auto-suspend + wait-for-suspend drop)"
if uv run main.py --warehouse-type both --scenarios sequential --qtm 2 \
      --sizes small,medium,large,xlarge --runs 3 >> "$LOG" 2>&1; then
  log "STEP 2 DONE: run 010 completed (rc=0)"
else
  log "STEP 2 WARN: run 010 exited non-zero (rc=$?) — continuing to enrich anyway"
fi

# --- 3. Settle + enrich + transform ----------------------------------------
WAIT_SECONDS=10800   # 3h: WAREHOUSE_METERING_HISTORY can lag 1-3h
log "STEP 3: sleeping ${WAIT_SECONDS}s for ACCOUNT_USAGE to settle"
sleep "$WAIT_SECONDS"

step() {
  local name="$1"; shift
  log "START [$name]"
  if "$@" >> "$LOG" 2>&1; then log "OK    [$name]"; else log "FAIL  [$name] rc=$?"; fi
}
step "enrich"      uv run snowflake/enrich_results.py
step "build-views" bash common/transformations/build_views.sh
step "update-viz"  uv run visualization/update_data.py

# Intentionally NO rebuild/redeploy here — Claude rewrites the article body
# for the new story first, then builds + redeploys when notified.

# --- Done ------------------------------------------------------------------
if grep -q "FAIL  \[" "$LOG"; then
  log "PIPELINE FINISHED WITH FAILURES"
  touch "$SENTINEL_FAIL"
else
  log "PIPELINE FINISHED CLEAN"
  touch "$SENTINEL_DONE"
fi
