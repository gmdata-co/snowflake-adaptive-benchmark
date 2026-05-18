#!/bin/bash
# Second XSMALL pass using the "no idle time" policy: drop each warehouse the
# instant its workload finishes (BENCHMARK_IMMEDIATE_DROP=1), so gen1 never
# bills an idle tail. Same matrix as xs_all.sh, fresh run_ids (016+).
#
# CHAINED, NOT CONCURRENT: waits for xs_all.sh to fully finish (its DONE or
# FAILED sentinel) before starting. Running both XSMALL matrices at once would
# make them contend for the Snowflake account and smear each other's timings
# and cost attribution, which defeats the comparison.
#
# Does enrich + build-views so the immediate-drop data is processed and
# queryable in DuckDB/dbt, but DELIBERATELY does NOT run update_data.py: the
# chart currently keys cells on (scenario, type, size, qtm) with no
# drop-policy dimension, so refreshing the JSON would overwrite the published
# wait-for-suspend XSMALL points. The no-idle series stays staged for the
# future viz work the user will spec out later.
#
# Survives session crashes (launched via nohup). Own sentinels.
cd "$(dirname "$0")"
LOG=xs_all_noidle.log
SENTINEL_DONE=xs_all_noidle.DONE
SENTINEL_FAIL=xs_all_noidle.FAILED
UPSTREAM_DONE=xs_all.DONE
UPSTREAM_FAIL=xs_all.FAILED
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

# --- 0. Wait for the wait-for-suspend pass to fully finish ------------------
log "STEP 0: waiting for xs_all.sh to finish (sentinel) before starting"
while [ ! -f "$UPSTREAM_DONE" ] && [ ! -f "$UPSTREAM_FAIL" ]; do
  sleep 60
done
if [ -f "$UPSTREAM_FAIL" ]; then
  log "NOTE: upstream xs_all reported FAILED; proceeding with no-idle pass anyway"
fi
log "STEP 0 DONE: upstream finished; starting no-idle XSMALL matrix"

export BENCHMARK_IMMEDIATE_DROP=1

# --- 1. q1 latency smoke (FATAL on failure) --------------------------------
if ! run_step "xsni-q1-latency-both" \
      uv run main.py --warehouse-type both --scenarios sequential \
        --queries 1 --sizes xsmall; then
  log "ABORT: XSMALL no-idle q1 smoke failed; not burning hours on the rest"
  touch "$SENTINEL_FAIL"
  exit 1
fi

# --- 2-5. Full XSMALL matrix, immediate-drop (non-fatal) -------------------
run_step "xsni-sequential-3x-both" \
  uv run main.py --warehouse-type both --scenarios sequential \
    --qtm 2 --sizes xsmall --runs 3

run_step "xsni-concurrent-qtm2-both" \
  uv run main.py --warehouse-type both --scenarios concurrent \
    --qtm 2 --sizes xsmall

run_step "xsni-concurrent-qtm8-adaptive" \
  uv run main.py --warehouse-type adaptive --scenarios concurrent \
    --qtm 8 --sizes xsmall

run_step "xsni-dml-qtm2-both" \
  uv run main.py --warehouse-type both --scenarios dml \
    --qtm 2 --sizes xsmall

# --- 6. Settle + enrich + transform (NO update-viz) ------------------------
WAIT_SECONDS=10800   # 3h: WAREHOUSE_METERING_HISTORY can lag 1-3h
log "STEP 6: sleeping ${WAIT_SECONDS}s for ACCOUNT_USAGE to settle"
sleep "$WAIT_SECONDS"

run_step "enrich"      uv run snowflake/enrich_results.py
run_step "build-views" bash common/transformations/build_views.sh
# NO update_data.py on purpose — see header.

# --- Done ------------------------------------------------------------------
if grep -q "FAIL  \[" "$LOG"; then
  log "PIPELINE FINISHED WITH FAILURES"
  touch "$SENTINEL_FAIL"
else
  log "PIPELINE FINISHED CLEAN"
  touch "$SENTINEL_DONE"
fi
