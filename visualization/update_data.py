"""
Update visualization JSON data from DuckDB run_summary view.

This script queries the run_summary dbt view and exports the data
to benchmarkData.json for the React visualization app.

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

# Scenario display names mapping
SCENARIO_LABELS = {
    "normal": "22 Sequential Queries",
    "coldstart": "5 Cold Start Queries",
    "concurrent": "22 Concurrent Queries",
    "ctas": "5 CTAS Queries",
    "dml": "DML Refresh",
}

# Paths
DB_PATH = project_root / "benchmark_results.duckdb"
OUTPUT_PATH = Path(__file__).parent / "src" / "data" / "benchmarkData.json"


def get_scenario_costs(conn: duckdb.DuckDBPyConnection) -> dict:
    """Get total credits/dbus per scenario/tier for proportional cost allocation."""
    query = """
    SELECT
        scenario,
        warehouse_tier,
        snow_total_credits,
        dbx_total_dbus
    FROM main.run_summary_agg
    """
    results = conn.execute(query).fetchall()

    costs = {}
    for row in results:
        scenario, tier, snow_credits, dbx_dbus = row
        key = f"{scenario}-{tier}"
        costs[key] = {
            "snow_credits": float(snow_credits) if snow_credits else 0,
            "dbx_dbus": float(dbx_dbus) if dbx_dbus else 0,
        }
    logger.info(f"Loaded scenario costs for {len(costs)} scenario/tier combinations")
    return costs


def get_query_details_data(
    conn: duckdb.DuckDBPyConnection, scenario_costs: dict
) -> list[dict]:
    """Query query_details view and return formatted data for visualization."""
    query = """
    SELECT
        run_id,
        scenario,
        warehouse_tier,
        query_num,
        ctas_variant,
        query_id_display,
        query_type,
        query_category,
        query_description,
        sql_snippet,
        full_sql,
        snow_warehouse_size,
        snow_warehouse_name,
        snow_execution_sec,
        snow_rows_produced,
        snow_error,
        dbx_warehouse_size,
        dbx_warehouse_name,
        dbx_execution_sec,
        dbx_rows_produced,
        dbx_error,
        snow_total_exec_time,
        dbx_total_exec_time
    FROM main.query_details
    ORDER BY
        CASE scenario
            WHEN 'normal' THEN 1
            WHEN 'coldstart' THEN 2
            WHEN 'concurrent' THEN 3
            WHEN 'ctas' THEN 4
            ELSE 5
        END,
        warehouse_tier,
        query_num,
        ctas_variant
    """

    results = conn.execute(query).fetchall()
    logger.info(f"Fetched {len(results)} rows from query_details")

    details = []
    for row in results:
        (
            run_id,
            scenario,
            warehouse_tier,
            query_num,
            ctas_variant,
            query_id_display,
            query_type,
            query_category,
            query_description,
            sql_snippet,
            full_sql,
            snow_warehouse_size,
            snow_warehouse_name,
            snow_execution_sec,
            snow_rows_produced,
            snow_error,
            dbx_warehouse_size,
            dbx_warehouse_name,
            dbx_execution_sec,
            dbx_rows_produced,
            dbx_error,
            snow_total_exec_time,
            dbx_total_exec_time,
        ) = row

        # Calculate proportional credits/dbus based on execution time share
        cost_key = f"{scenario}-{warehouse_tier}"
        costs = scenario_costs.get(cost_key, {})

        # Snowflake proportional credits
        snow_credits = None
        if (
            snow_execution_sec is not None
            and snow_total_exec_time is not None
            and snow_total_exec_time > 0
        ):
            proportion = float(snow_execution_sec) / float(snow_total_exec_time)
            total_credits = costs.get("snow_credits", 0)
            if total_credits > 0:
                snow_credits = round(proportion * total_credits, 6)

        # Databricks proportional dbus
        dbx_dbus = None
        if (
            dbx_execution_sec is not None
            and dbx_total_exec_time is not None
            and dbx_total_exec_time > 0
        ):
            proportion = float(dbx_execution_sec) / float(dbx_total_exec_time)
            total_dbus = costs.get("dbx_dbus", 0)
            if total_dbus > 0:
                dbx_dbus = round(proportion * total_dbus, 6)

        detail = {
            "id": f"{scenario}-{warehouse_tier}-{run_id}-{query_id_display}",
            "runId": run_id,
            "scenario": scenario,
            "warehouseTier": warehouse_tier,
            "queryNum": query_num,
            "ctasVariant": ctas_variant,
            "queryIdDisplay": query_id_display,
            "queryType": query_type,
            "queryCategory": query_category,
            "queryDescription": query_description,
            "sqlSnippet": sql_snippet,
            "fullSql": full_sql,
            "snowflake": {
                "warehouseSize": snow_warehouse_size,
                "warehouseName": snow_warehouse_name,
                "executionSec": (
                    round(float(snow_execution_sec), 2)
                    if snow_execution_sec is not None
                    else None
                ),
                "credits": snow_credits,
                "rowsProduced": snow_rows_produced,
                "error": snow_error if snow_error else None,
            }
            if snow_warehouse_size
            else None,
            "databricks": {
                "warehouseSize": dbx_warehouse_size,
                "warehouseName": dbx_warehouse_name,
                "executionSec": (
                    round(float(dbx_execution_sec), 2)
                    if dbx_execution_sec is not None
                    else None
                ),
                "dbus": dbx_dbus,
                "rowsProduced": dbx_rows_produced,
                "error": dbx_error if dbx_error else None,
            }
            if dbx_warehouse_size
            else None,
        }
        details.append(detail)

    return details


def get_run_summary_data(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    """Query run_summary_agg view and return formatted comparison data."""
    query = """
    SELECT
        scenario,
        warehouse_tier,
        snow_warehouse_size,
        dbx_warehouse_size,
        snow_wall_clock_seconds,
        dbx_wall_clock_seconds,
        snow_total_credits,
        dbx_total_dbus,
        snow_total_cost,
        dbx_total_cost
    FROM main.run_summary_agg
    ORDER BY
        CASE scenario
            WHEN 'normal' THEN 1
            WHEN 'coldstart' THEN 2
            WHEN 'concurrent' THEN 3
            WHEN 'ctas' THEN 4
            ELSE 5
        END,
        warehouse_tier
    """

    results = conn.execute(query).fetchall()
    logger.info(f"Fetched {len(results)} rows from run_summary_agg")

    comparisons = []
    for row in results:
        (
            scenario,
            tier,
            snow_size,
            dbx_size,
            snow_time,
            dbx_time,
            snow_credits,
            dbx_dbus,
            snow_cost,
            dbx_cost,
        ) = row

        # Build platform data - set to None if warehouse_size is missing (no data for that platform)
        # Use `is not None` checks since 0 is a valid value but falsy in Python
        snowflake_data = None
        if snow_size:
            snowflake_data = {
                "size": snow_size,
                "label": f"Snowflake {snow_size.title()}",
                "time": round(float(snow_time), 2) if snow_time is not None else None,
                "credits": round(float(snow_credits), 4) if snow_credits is not None else None,
                "cost": round(float(snow_cost), 2) if snow_cost is not None else None,
            }

        databricks_data = None
        if dbx_size:
            databricks_data = {
                "size": dbx_size,
                "label": f"Databricks {dbx_size.title()}",
                "time": round(float(dbx_time), 2) if dbx_time is not None else None,
                "dbus": round(float(dbx_dbus), 4) if dbx_dbus is not None else None,
                "cost": round(float(dbx_cost), 2) if dbx_cost is not None else None,
            }

        comparison = {
            "id": f"{scenario}-{tier}",
            "scenario": scenario,
            "scenarioLabel": SCENARIO_LABELS.get(scenario, scenario.title()),
            "warehouseTier": tier,
            "snowflake": snowflake_data,
            "databricks": databricks_data,
        }
        comparisons.append(comparison)

    return comparisons


def update_visualization_data():
    """Main function to update the visualization JSON data."""
    logger.info(f"Connecting to DuckDB at {DB_PATH}")

    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        # Load scenario costs for proportional allocation
        scenario_costs = get_scenario_costs(conn)

        comparisons = get_run_summary_data(conn)
        query_details = get_query_details_data(conn, scenario_costs)

        if not comparisons:
            logger.warning("No data found in run_summary view")
            sys.exit(1)

        output = {
            "comparisons": comparisons,
            "queryDetails": query_details,
            "exportedAt": datetime.now().isoformat(),
        }

        # Ensure output directory exists
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(OUTPUT_PATH, "w") as f:
            json.dump(output, f, indent=2)

        logger.info(
            f"Exported {len(comparisons)} comparisons and {len(query_details)} query details to {OUTPUT_PATH}"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    update_visualization_data()
