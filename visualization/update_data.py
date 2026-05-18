"""
Update visualization JSON data from DuckDB.

Queries the adaptive_vs_gen1_summary dbt view and writes benchmarkData.json
in a shape the React chart consumes. The legacy schema used `gen1` and
`adaptive` keys per comparison row; this script reuses that shape but maps:

    gen1 warehouse runs    -> "gen1" key
    adaptive warehouse runs -> "adaptive" key

so the existing ScenarioSummaryChart renders 8 points per scenario (4 sizes ×
2 warehouse types) with no JSX changes required. Labels and tooltips reflect
the actual warehouse_type / QTM rather than vendor names — chart logos can be
updated separately when convenient.

Each (scenario, qtm) combination becomes its own scenario panel so adaptive
concurrent at QTM=2 vs QTM=8 appear as two distinct panels.

Usage:
    uv run visualization/update_data.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for common imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.logging_config import get_logger  # noqa: E402
import duckdb  # noqa: E402

logger = get_logger(__name__)

DB_PATH = project_root / "benchmark_results.duckdb"
OUTPUT_PATH = Path(__file__).parent / "src" / "data" / "benchmarkData.json"

# Pretty labels per scenario id (without QTM suffix).
SCENARIO_BASE_LABELS = {
    "sequential": "22 Sequential Queries",
    "concurrent": "22 Concurrent Queries",
    "dml": "DML Refresh",
    "single_query": "Single Query (q1) Latency",
}


# --- Idle-policy series -----------------------------------------------------
# idle_policy is now a REAL run-time column on every result row (no more
# guessing by run_id, no run_policy.json manifest). For gen1 it is one of:
#
#   wait_for_suspend : gen1 left running until AUTO_SUSPEND fired, THEN dropped
#                       -> the idle tail is billed (realistic steady-state cost)
#   immediate_drop   : gen1 killed the instant the workload finished
#                       -> no idle tail billed ("kill right away")
#
# Adaptive has no idle concept (per-query billed) and is recorded as 'n_a';
# it is policy-invariant, so the SAME adaptive points appear under BOTH toggle
# states. The dashboard toggle simply filters gen1 rows by this column.
POLICY_WAIT = "wait_for_suspend"
POLICY_IMMEDIATE = "immediate_drop"
DEFAULT_POLICY = POLICY_WAIT  # the "realistic steady state" view

# Display metadata for the App.jsx toggle/banner (was run_policy.json).
POLICY_META = {
    POLICY_WAIT: {
        "tag": "WAIT-FOR-SUSPEND",
        "short": "With idle tail",
        "label": "Idle billed: gen1 left to auto-suspend before drop (realistic steady state)",
    },
    POLICY_IMMEDIATE: {
        "tag": "KILL-IMMEDIATELY",
        "short": "No idle tail",
        "label": "No idle: gen1 killed the instant the workload finished",
    },
}


def _scenario_panel_id(scenario: str, qtm) -> str:
    """Build a synthetic panel id. Adaptive QTM variants get separate panels."""
    if qtm is None:
        return scenario
    return f"{scenario}_qtm{qtm}"


def _scenario_label(scenario: str, qtm) -> str:
    base = SCENARIO_BASE_LABELS.get(scenario, scenario.title())
    if qtm is None:
        return base
    return f"{base} (QTM={qtm})"


def get_summary_rows(conn: duckdb.DuckDBPyConnection):
    """Read every (run_id, scenario, warehouse_type, size, qtm) row."""
    query = """
    SELECT
        run_id,
        scenario,
        warehouse_type,
        warehouse_size,
        qtm,
        idle_policy,
        warehouse_tier,
        total_wall_clock_seconds,
        total_credits,
        total_cost_usd,
        query_count
    FROM main.adaptive_vs_gen1_summary
    ORDER BY scenario, warehouse_tier, warehouse_type, qtm,
             CAST(run_id AS BIGINT)
    """
    rows = conn.execute(query).fetchall()
    logger.info(f"Fetched {len(rows)} rows from adaptive_vs_gen1_summary")
    return rows


def build_comparisons(rows, policy=None):
    """
    Pivot rows so each (scenario, qtm, warehouse_tier) becomes one comparison
    with both 'gen1' (= gen1) and 'adaptive' (= adaptive) sub-records.

    Idle-policy selection is PER CELL (per scenario/type/qtm/tier) and reads
    the real `idle_policy` column. A row matches the requested `policy` when
    its idle_policy equals it, OR the warehouse is adaptive (adaptive has no
    idle concept, so the same adaptive points show under BOTH toggle states).
    Within a matching policy the highest run_id wins. The per-cell `any`
    fallback is kept only as a safety net for a genuinely missing cell
    (flagged `fallback=True`); with a full matrix per policy it stays unused.

    Gen1 has qtm=NULL and lives on every adaptive QTM panel? No — gen1 belongs
    on its own panel because qtm doesn't apply. To keep the chart at 8 points
    per panel (4 sizes × 2 types), we attach the SAME gen1 result to every
    adaptive-QTM panel that exists for that scenario.
    """
    # cells[scenario][wtype][bucket][tier] = {"target": rec|None, "any": rec}
    # rows arrive ORDER BY ... run_id ASC, so "last seen" == highest run_id.
    cells = {}
    for r in rows:
        (run_id, scenario, wtype, size, qtm, idle_policy, tier,
         time_s, credits, cost, qcount) = r
        # The single-query (q1) latency experiment was run as
        # `--scenarios sequential --queries 1`, so it lands as scenario
        # 'sequential' too. Split it into its own panel so it doesn't collide
        # with the full 22-query sequential runs.
        if scenario == "sequential" and qcount == 1:
            scenario = "single_query"
        bucket_key = qtm if wtype == "adaptive" else None
        rec = {
            "run_id": run_id,
            "size": size,
            "qtm": qtm,
            "time": float(time_s) if time_s is not None else None,
            "credits": float(credits) if credits is not None else None,
            "cost": float(cost) if cost is not None else None,
        }
        slot = (
            cells.setdefault(scenario, {})
            .setdefault(wtype, {})
            .setdefault(bucket_key, {})
            .setdefault(tier, {"target": None, "any": None})
        )
        slot["any"] = rec
        # Adaptive is policy-invariant -> always matches. Gen1 matches only
        # the series whose idle_policy it was actually run under.
        matches = (
            policy is None
            or wtype == "adaptive"
            or idle_policy == policy
        )
        if matches:
            slot["target"] = rec

    # Resolve each cell: prefer the target-policy record, else fall back to
    # the full-prior-run record (flagged).
    by_scenario = {}
    for scenario, by_type in cells.items():
        for wtype, by_bucket in by_type.items():
            for bucket, by_tier in by_bucket.items():
                for tier, slot in by_tier.items():
                    chosen = slot["target"]
                    fallback = False
                    if chosen is None:
                        chosen = slot["any"]
                        fallback = True
                    if chosen is None:
                        continue
                    chosen = {**chosen, "fallback": fallback}
                    (
                        by_scenario.setdefault(scenario, {})
                        .setdefault(wtype, {})
                        .setdefault(bucket, {})
                    )[tier] = chosen

    comparisons = []
    for scenario, by_type in by_scenario.items():
        gen1_buckets = by_type.get("gen1", {})
        adaptive_buckets = by_type.get("adaptive", {})

        gen1_data = gen1_buckets.get(None, {})  # qtm=None bucket
        if adaptive_buckets:
            # One panel per adaptive QTM value.
            for qtm, adapt_data in adaptive_buckets.items():
                panel_id = _scenario_panel_id(scenario, qtm)
                comparisons.extend(
                    _emit_panel_rows(panel_id, scenario, qtm, gen1_data, adapt_data)
                )
        else:
            # Gen1 only: still emit one panel with the gen1 points.
            comparisons.extend(
                _emit_panel_rows(scenario, scenario, None, gen1_data, {})
            )

    return comparisons


def _emit_panel_rows(panel_id, scenario, qtm, gen1_by_tier, adaptive_by_tier):
    """Emit one comparison row per warehouse_tier for a given panel."""
    label = _scenario_label(scenario, qtm)
    tiers = sorted(set(gen1_by_tier) | set(adaptive_by_tier))
    rows = []
    for tier in tiers:
        g = gen1_by_tier.get(tier)
        a = adaptive_by_tier.get(tier)

        # The chart's existing JSX uses `gen1` and `adaptive` keys.
        # We reuse those keys: gen1 = gen1, adaptive = adaptive.
        gen1_data = None
        if g:
            gen1_data = {
                "size": g["size"],
                "label": f"Gen1 {g['size']}",
                "time": round(g["time"], 2) if g["time"] is not None else None,
                "credits": round(g["credits"], 4) if g["credits"] is not None else None,
                "cost": round(g["cost"], 2) if g["cost"] is not None else None,
                "fallback": bool(g.get("fallback")),
            }

        adaptive_data = None
        if a:
            qtm_suffix = f" QTM={a['qtm']}" if a["qtm"] is not None else ""
            adaptive_data = {
                "size": a["size"],
                "label": f"Adaptive {a['size']}{qtm_suffix}",
                "time": round(a["time"], 2) if a["time"] is not None else None,
                "dbus": round(a["credits"], 4) if a["credits"] is not None else None,
                "cost": round(a["cost"], 2) if a["cost"] is not None else None,
                "fallback": bool(a.get("fallback")),
            }

        # Row is flagged fallback only if a PRESENT sub-record is fallback.
        row_fallback = bool(
            (gen1_data and gen1_data["fallback"])
            or (adaptive_data and adaptive_data["fallback"])
        )
        rows.append({
            "id": f"{panel_id}-{tier}",
            "scenario": panel_id,
            "scenarioLabel": label,
            "warehouseTier": tier,
            "gen1": gen1_data,
            "adaptive": adaptive_data,
            "policyFallback": row_fallback,
        })
    return rows


CCFRESH_DB = project_root / ".ccfresh" / "benchmark_results.duckdb"
_CREDIT_PRICE = 2.00  # app re-prices from credits; cost = credits * price
_TIER_SIZE = {1: "XSMALL", 2: "SMALL", 3: "MEDIUM", 4: "LARGE", 5: "XLARGE"}
# The concurrent panels come from one fresh single concurrent run
# (.ccfresh), charted per idle_policy so Chapter 3's tail / no-tail toggle is
# real: gen1 wait_for_suspend feeds the "with idle tail" series, gen1
# immediate_drop the "no idle tail" series, adaptive (n_a) appears in both.
# Single run by user choice; presented as plain data, no methodology narration.
_CONC_PANELS = {"concurrent_qtm2": 2, "concurrent_qtm8": 8}


def _load_ccfresh_cells():
    """(wtype,size,qtm,idle_policy) -> (time_s, credits) from the fresh run."""
    if not CCFRESH_DB.exists():
        return None
    conn = duckdb.connect(str(CCFRESH_DB), read_only=True)
    try:
        rows = conn.execute(
            """
            WITH cost AS (
              SELECT warehouse_type, warehouse_size,
                     COALESCE(qtm,-1) AS qtm, idle_policy,
                     SUM(COALESCE(credits_used_compute,0)
                       + COALESCE(credits_used_cloud_services,0)) AS credits
              FROM snowflake_results WHERE scenario='concurrent'
              GROUP BY 1,2,3,4),
            wc AS (
              SELECT warehouse_type, warehouse_size,
                     COALESCE(qtm,-1) AS qtm, idle_policy,
                     SUM(total_wall_clock_seconds) AS t
              FROM run_metadata WHERE scenario='concurrent'
              GROUP BY 1,2,3,4)
            SELECT cost.warehouse_type, cost.warehouse_size, cost.qtm,
                   cost.idle_policy, wc.t, cost.credits
            FROM cost JOIN wc
              USING (warehouse_type, warehouse_size, qtm, idle_policy)
            """
        ).fetchall()
    finally:
        conn.close()
    m = {}
    for wt, size, qtm, pol, t, cr in rows:
        m[(wt, size, int(qtm), pol)] = (
            float(t) if t is not None else None,
            float(cr) if cr is not None else None,
        )
    return m


def _apply_concurrent_fresh(policies_out):
    """Override concurrent panels from the fresh single run, per idle_policy."""
    cells = _load_ccfresh_cells()
    if not cells:
        logger.info("No .ccfresh DB; concurrent panels left as summary-view.")
        return
    n = 0
    for series_pol, series in policies_out.items():
        for row in series["comparisons"]:
            qtm = _CONC_PANELS.get(row["scenario"])
            if qtm is None:
                continue
            size = _TIER_SIZE.get(row["warehouseTier"])
            if not size:
                continue
            # gen1 follows the toggle; adaptive is policy-invariant (n_a).
            g = cells.get(("gen1", size, -1, series_pol))
            a = cells.get(("adaptive", size, qtm, "n_a"))
            if g and None not in g:
                gt, gc = g
                row["gen1"] = {
                    "size": size,
                    "label": f"Gen1 {size}",
                    "time": round(gt, 2),
                    "credits": round(gc, 4),
                    "cost": round(gc * _CREDIT_PRICE, 2),
                    "fallback": False,
                }
            if a and None not in a:
                at, ac = a
                row["adaptive"] = {
                    "size": size,
                    "label": f"Adaptive {size} QTM={qtm}",
                    "time": round(at, 2),
                    "dbus": round(ac, 4),
                    "cost": round(ac * _CREDIT_PRICE, 2),
                    "fallback": False,
                }
            row["policyFallback"] = False
            n += 1
    logger.info(
        f"Applied fresh single concurrent run to {n} panel rows "
        f"(per idle_policy; Ch3 tail/no-tail toggle now live)."
    )


def update_visualization_data():
    logger.info(f"Connecting to DuckDB at {DB_PATH}")
    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        rows = get_summary_rows(conn)

        # Build a full comparison set per idle policy. Fallback is per-cell
        # (handled inside build_comparisons): each policy is the COMPLETE
        # matrix — real results where that policy was actually run, the full
        # prior run elsewhere (flagged), with XS tacked on as its runs land.
        policies_out = {
            POLICY_WAIT: {"comparisons": build_comparisons(rows, policy=POLICY_WAIT)},
            POLICY_IMMEDIATE: {"comparisons": build_comparisons(rows, policy=POLICY_IMMEDIATE)},
        }
        if (not policies_out[POLICY_WAIT]["comparisons"]
                and not policies_out[POLICY_IMMEDIATE]["comparisons"]):
            logger.warning("No data found in adaptive_vs_gen1_summary view")
            sys.exit(1)

        _apply_concurrent_fresh(policies_out)

        default_comps = policies_out[DEFAULT_POLICY]["comparisons"]
        output = {
            "defaultPolicy": DEFAULT_POLICY,
            "policyMeta": POLICY_META,
            "policies": policies_out,
            # Back-compat: anything still reading `.comparisons` gets the
            # default policy's set.
            "comparisons": default_comps,
            "queryDetails": [],  # query_details view is disabled in this experiment
            "exportedAt": datetime.now().isoformat(),
        }
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w") as f:
            json.dump(output, f, indent=2)

        for pol in (POLICY_WAIT, POLICY_IMMEDIATE):
            comps = policies_out[pol]["comparisons"]
            fb = sum(1 for c in comps if c.get("policyFallback"))
            scen = sorted({c["scenario"] for c in comps})
            logger.info(
                f"[{pol}] {len(comps)} comparisons, {len(scen)} panels "
                f"({fb} fallback rows): {scen}"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    update_visualization_data()
