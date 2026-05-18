#!/usr/bin/env python3
"""
Aggregate the concurrent-scenario replication across N independent rep DBs.

For each rep duckdb (enriched), compute per cell
(warehouse_type, warehouse_size, qtm) for scenario='concurrent':
  * time  = SUM(run_metadata.total_wall_clock_seconds) for that run
  * cost  = (SUM(credits_used_compute)+SUM(credits_used_cloud_services)) * 2

Each rep contributes ONE observation per cell. Across reps we report
n / median / mean / min / max / stdev so we can tell a real
gen1-vs-adaptive difference from run-to-run noise, and judge whether the
old "Adaptive's home turf — decisively cheaper" claim holds.

Usage: uv run aggregate_concurrent.py rep1.duckdb rep2.duckdb ...
"""

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import duckdb

CREDIT_PRICE = 2.00
SIZE_ORDER = {"XSMALL": 1, "SMALL": 2, "MEDIUM": 3, "LARGE": 4, "XLARGE": 5}


def per_rep_cells(db_path):
    """Return {(wtype,size,qtm): {'time':float,'cost':float}} for one rep."""
    c = duckdb.connect(db_path, read_only=True)
    try:
        rows = c.execute(
            """
            WITH cost AS (
              SELECT run_id, warehouse_type, warehouse_size, qtm,
                     SUM(COALESCE(credits_used_compute,0)
                       + COALESCE(credits_used_cloud_services,0)) AS credits
              FROM snowflake_results
              WHERE scenario='concurrent'
              GROUP BY 1,2,3,4),
            wc AS (
              SELECT run_id, warehouse_type, warehouse_size, qtm,
                     SUM(total_wall_clock_seconds) AS t
              FROM run_metadata
              WHERE scenario='concurrent'
              GROUP BY 1,2,3,4)
            SELECT cost.warehouse_type, cost.warehouse_size,
                   COALESCE(cost.qtm,-1) AS qtm,
                   wc.t, cost.credits
            FROM cost JOIN wc
              ON cost.run_id=wc.run_id
             AND cost.warehouse_type=wc.warehouse_type
             AND cost.warehouse_size=wc.warehouse_size
             AND COALESCE(cost.qtm,-1)=COALESCE(wc.qtm,-1)
            """
        ).fetchall()
    finally:
        c.close()
    out = {}
    for wt, size, qtm, t, credits in rows:
        out[(wt, size, int(qtm))] = {
            "time": float(t) if t is not None else None,
            "cost": round(float(credits) * CREDIT_PRICE, 4)
            if credits is not None
            else None,
        }
    return out


def stats(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return {
        "n": len(vals),
        "median": round(statistics.median(vals), 3),
        "mean": round(statistics.fmean(vals), 3),
        "min": round(min(vals), 3),
        "max": round(max(vals), 3),
        "stdev": round(statistics.pstdev(vals), 3) if len(vals) > 1 else 0.0,
    }


def main(db_paths):
    series = defaultdict(lambda: {"time": [], "cost": []})
    n_reps = 0
    for p in db_paths:
        if not Path(p).exists():
            print(f"!! missing {p}", file=sys.stderr)
            continue
        n_reps += 1
        for cell, m in per_rep_cells(p).items():
            series[cell]["time"].append(m["time"])
            series[cell]["cost"].append(m["cost"])

    agg = {}
    for cell, sv in series.items():
        wt, size, qtm = cell
        agg[f"{wt}|{size}|{qtm}"] = {
            "warehouse_type": wt,
            "warehouse_size": size,
            "qtm": None if qtm == -1 else qtm,
            "time": stats(sv["time"]),
            "cost": stats(sv["cost"]),
        }

    out_path = Path(db_paths[0]).resolve().parent.parent / "summary.json"
    out_path.write_text(json.dumps({"n_reps": n_reps, "cells": agg}, indent=2))

    # Human-readable verdict table: gen1 vs adaptive QTM2 vs QTM8 cost.
    def get(wt, size, qtm):
        # gen1 has no qtm -> stored under the -1 sentinel; normalize None->-1.
        q = -1 if qtm is None else qtm
        return agg.get(f"{wt}|{size}|{q}")

    print(f"\n=== CONCURRENT replication: {n_reps} reps ===")
    print("cost $ shown as median [min..max] (n)\n")
    hdr = f"{'size':7} | {'gen1':22} | {'adaptive QTM2':22} | {'adaptive QTM8':22} | verdict (QTM2 vs gen1)"
    print(hdr)
    print("-" * len(hdr))
    for size in sorted(SIZE_ORDER, key=SIZE_ORDER.get):
        g = get("gen1", size, None)
        a2 = get("adaptive", size, 2)
        a8 = get("adaptive", size, 8)

        def fmt(x):
            if not x or not x["cost"]:
                return "—"
            cc = x["cost"]
            return f"{cc['median']:.2f} [{cc['min']:.2f}..{cc['max']:.2f}] (n{cc['n']})"

        verdict = "—"
        if g and a2 and g["cost"] and a2["cost"]:
            gm, am = g["cost"]["median"], a2["cost"]["median"]
            # robust only if medians differ by more than the larger spread
            spread = max(
                g["cost"]["max"] - g["cost"]["min"],
                a2["cost"]["max"] - a2["cost"]["min"],
            )
            diff = gm - am
            if abs(diff) <= spread:
                verdict = f"WITHIN NOISE (Δ={diff:+.2f}, spread≈{spread:.2f})"
            elif diff > 0:
                verdict = f"adaptive cheaper by {diff:+.2f} (robust)"
            else:
                verdict = f"GEN1 cheaper by {-diff:.2f} (robust)"
        print(f"{size:7} | {fmt(g):22} | {fmt(a2):22} | {fmt(a8):22} | {verdict}")

    print(f"\nFull stats -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: aggregate_concurrent.py rep1.duckdb [rep2.duckdb ...]")
        sys.exit(1)
    main(sys.argv[1:])
