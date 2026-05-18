#!/bin/bash
# Re-run only the two DML steps that failed on the missing BENCHMARK database.
cd "$(dirname "$0")"
LOG=run_all.log

run_step() {
  local name="$1"; shift
  echo "==== START [$name] $(date '+%H:%M:%S') ====" | tee -a "$LOG"
  if "$@" >> "$LOG" 2>&1; then
    echo "==== OK    [$name] $(date '+%H:%M:%S') ====" | tee -a "$LOG"
  else
    echo "==== FAIL  [$name] rc=$? $(date '+%H:%M:%S') ====" | tee -a "$LOG"
  fi
}

run_step "adaptive-dml-qtm2-retry" uv run main.py --warehouse-type adaptive --scenarios dml --qtm 2
run_step "gen1-dml-retry"          uv run main.py --warehouse-type gen1     --scenarios dml
echo "==== DML RETRY DONE $(date '+%H:%M:%S') ====" | tee -a "$LOG"
