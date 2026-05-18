#!/bin/bash
# Waits for ACCOUNT_USAGE to settle, then enriches + builds views + refreshes
# the chart data. Single-shot: the enricher only fills rows where
# compilation_time_ms IS NULL, so this must run AFTER both QUERY_HISTORY and
# WAREHOUSE_METERING_HISTORY are populated (metering can lag ~1-3h).
cd "$(dirname "$0")"
LOG=enrich.log
: > "$LOG"

WAIT_SECONDS="${1:-7200}"   # default 2h; override by passing arg
echo "==== ENRICH PIPELINE: sleeping ${WAIT_SECONDS}s until ACCOUNT_USAGE settles $(date '+%H:%M:%S') ====" | tee -a "$LOG"
sleep "$WAIT_SECONDS"

step() {
  local name="$1"; shift
  echo "==== START [$name] $(date '+%H:%M:%S') ====" | tee -a "$LOG"
  if "$@" >> "$LOG" 2>&1; then
    echo "==== OK    [$name] $(date '+%H:%M:%S') ====" | tee -a "$LOG"
  else
    echo "==== FAIL  [$name] rc=$? $(date '+%H:%M:%S') ====" | tee -a "$LOG"
  fi
}

step "enrich"      uv run snowflake/enrich_results.py
step "build-views" bash common/transformations/build_views.sh
step "update-viz"  uv run visualization/update_data.py
echo "==== ENRICH PIPELINE DONE $(date '+%H:%M:%S') ====" | tee -a "$LOG"
