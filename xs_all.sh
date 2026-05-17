#!/bin/bash
# Add the XSMALL tier to every article panel.
#
# Runs the full benchmark matrix at --sizes xsmall ONLY, each main.py call
# getting its own auto-incremented run_id. XSMALL cells are brand new, so
# update_data.py (which picks the highest run_id per scenario/type/size/qtm
# cell) simply adds a 5th point to every existing panel without disturbing
# the S/M/L/XL points already published.
#
# Matrix mirrors the original run_all_experiments.sh + the 3x sequential:
#   1. q1 latency, both types        -> single_query panel (also XS smoke test)
#   2. sequential 3x, both types     -> Chapter 2 continuous-workload panel
#   3. concurrent QTM2, both types   -> concurrent QTM2 panel
#   4. concurrent QTM8, adaptive     -> concurrent QTM8 panel
#   5. DML QTM2, both types          -> DML panel
#
# Step 1 is fatal: if XSMALL warehouse creation is broken, every later step
# would waste hours, so we abort. Steps 2-5 log failures but continue so one
# bad scenario doesn't cost the whole unattended run.
#
# Stops after refreshing the chart JSON ON PURPOSE: Claude rebuilds the viz
# and the user reviews/deploys. Survives session crashes (launched via nohup).
cd "$(dirname "$0")"
LOG=xs_all.log
SENTINEL_DONE=xs_all.DONE
SENTINEL_FAIL=xs_all.FAILED
rm -f "$SENTINEL_DONE" "$SENTINEL_FAIL"
: > "$LOG"

log() { echo "==== $* $(date '+%Y-%m-%d %H:%M:%S') ====" | tee -a "$LOG"; }

run_step() {
  local name="$1"; shift
  log "START [$name]"
  if "$@" >> "$LOG" 2>&1; then
    log "OK    [$name]"
    return 0
  else
    log "FAIL  [$name] rc=$?"
    return 1
  fi
}

# --- 1. q1 latency smoke (FATAL on failure) --------------------------------
if ! run_step "xs-q1-latency-both" \
      uv run main.py --warehouse-type both --scenarios sequential \
        --queries 1 --sizes xsmall; then
  log "ABORT: XSMALL q1 smoke failed; not burning hours on the rest"
  touch "$SENTINEL_FAIL"
  exit 1
fi

# --- 2-5. Full XSMALL matrix (non-fatal) -----------------------------------
run_step "xs-sequential-3x-both" \
  uv run main.py --warehouse-type both --scenarios sequential \
    --qtm 2 --sizes xsmall --runs 3

run_step "xs-concurrent-qtm2-both" \
  uv run main.py --warehouse-type both --scenarios concurrent \
    --qtm 2 --sizes xsmall

run_step "xs-concurrent-qtm8-adaptive" \
  uv run main.py --warehouse-type adaptive --scenarios concurrent \
    --qtm 8 --sizes xsmall

run_step "xs-dml-qtm2-both" \
  uv run main.py --warehouse-type both --scenarios dml \
    --qtm 2 --sizes xsmall

# --- 6. Settle + enrich + transform + refresh chart JSON -------------------
WAIT_SECONDS=10800   # 3h: WAREHOUSE_METERING_HISTORY can lag 1-3h
log "STEP 6: sleeping ${WAIT_SECONDS}s for ACCOUNT_USAGE to settle"
sleep "$WAIT_SECONDS"

run_step "enrich"      uv run snowflake/enrich_results.py
run_step "build-views" bash common/transformations/build_views.sh
run_step "update-viz"  uv run visualization/update_data.py

# Intentionally NO viz rebuild/redeploy — Claude rebuilds, user reviews/deploys.

# --- Done ------------------------------------------------------------------
if grep -q "FAIL  \[" "$LOG"; then
  log "PIPELINE FINISHED WITH FAILURES"
  touch "$SENTINEL_FAIL"
else
  log "PIPELINE FINISHED CLEAN"
  touch "$SENTINEL_DONE"
fi
