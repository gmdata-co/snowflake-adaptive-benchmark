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
}

# Paths
DB_PATH = project_root / "benchmark_results.duckdb"
OUTPUT_PATH = Path(__file__).parent / "src" / "data" / "benchmarkData.json"


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
        comparisons = get_run_summary_data(conn)

        if not comparisons:
            logger.warning("No data found in run_summary view")
            sys.exit(1)

        output = {
            "comparisons": comparisons,
            "exportedAt": datetime.now().isoformat(),
        }

        # Ensure output directory exists
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(OUTPUT_PATH, "w") as f:
            json.dump(output, f, indent=2)

        logger.info(f"Exported {len(comparisons)} comparisons to {OUTPUT_PATH}")

    finally:
        conn.close()


if __name__ == "__main__":
    update_visualization_data()
