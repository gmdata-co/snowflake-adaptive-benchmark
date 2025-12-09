"""Export benchmark data from DuckDB to JSON for the visualization app."""

import json
from datetime import datetime
from pathlib import Path

import duckdb

# Scenario display names
SCENARIO_LABELS = {
    "normal": "23 Sequential Queries",
    "coldstart": "5 Cold Start Queries",
    "concurrent": "23 Concurrent Queries",
}

def export_benchmark_data():
    """Query run_summary and export to JSON."""
    db_path = Path(__file__).parent.parent.parent / "benchmark_results.duckdb"
    output_path = Path(__file__).parent.parent / "src" / "data" / "benchmarkData.json"

    conn = duckdb.connect(str(db_path), read_only=True)

    # Query the run_summary table
    query = """
    SELECT
        scenario,
        warehouse_tier,
        snow_warehouse_size,
        dbx_warehouse_size,
        snow_wall_clock_seconds,
        dbx_wall_clock_seconds,
        snow_total_cost,
        dbx_total_cost
    FROM main.run_summary
    ORDER BY
        CASE scenario
            WHEN 'normal' THEN 1
            WHEN 'coldstart' THEN 2
            WHEN 'concurrent' THEN 3
        END,
        warehouse_tier
    """

    results = conn.execute(query).fetchall()
    conn.close()

    comparisons = []
    for row in results:
        (scenario, tier, snow_size, dbx_size,
         snow_time, dbx_time, snow_cost, dbx_cost) = row

        comparison = {
            "id": f"{scenario}-{tier}",
            "scenario": scenario,
            "scenarioLabel": SCENARIO_LABELS.get(scenario, scenario),
            "warehouseTier": tier,
            "snowflake": {
                "size": snow_size,
                "label": f"Snowflake {snow_size.title()}",
                "time": round(float(snow_time), 2),
                "cost": round(float(snow_cost), 2),
            },
            "databricks": {
                "size": dbx_size,
                "label": f"Databricks {dbx_size.title()}",
                "time": round(float(dbx_time), 2),
                "cost": round(float(dbx_cost), 2),
            },
        }
        comparisons.append(comparison)

    output = {
        "comparisons": comparisons,
        "exportedAt": datetime.now().isoformat(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Exported {len(comparisons)} comparisons to {output_path}")

if __name__ == "__main__":
    export_benchmark_data()
