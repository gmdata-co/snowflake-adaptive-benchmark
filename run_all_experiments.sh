#!/bin/bash
# Orchestrates the full remaining benchmark matrix. Each step is independent:
# a failure is logged but does NOT abort the rest (so one bad scenario doesn't
# cost us the whole unattended run). Progress is appended to run_all.log.

cd "$(dirname "$0")"
LOG=run_all.log
: > "$LOG"

run_step() {
  local name="$1"; shift
  echo "==== START [$name] $(date '+%H:%M:%S') ====" | tee -a "$LOG"
  if "$@" >> "$LOG" 2>&1; then
    echo "==== OK    [$name] $(date '+%H:%M:%S') ====" | tee -a "$LOG"
  else
    echo "==== FAIL  [$name] rc=$? $(date '+%H:%M:%S') ====" | tee -a "$LOG"
  fi
}

run_step "q1-latency-both"      uv run main.py --warehouse-type both     --scenarios sequential --queries 1
run_step "adaptive-conc-qtm2"   uv run main.py --warehouse-type adaptive --scenarios concurrent --qtm 2
run_step "adaptive-conc-qtm8"   uv run main.py --warehouse-type adaptive --scenarios concurrent --qtm 8
run_step "gen1-concurrent"      uv run main.py --warehouse-type gen1     --scenarios concurrent
run_step "adaptive-dml-qtm2"    uv run main.py --warehouse-type adaptive --scenarios dml --qtm 2
run_step "gen1-dml"             uv run main.py --warehouse-type gen1     --scenarios dml

echo "==== ALL STEPS DONE $(date '+%H:%M:%S') ====" | tee -a "$LOG"
