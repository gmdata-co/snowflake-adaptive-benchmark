{{
    config(
        materialized='view'
    )
}}

-- Aggregated run summary without run_id
-- Sums wall clock times and costs across all runs for each scenario/tier combination
-- Used by visualization to show total benchmark work

SELECT
    scenario,
    warehouse_tier,
    MAX(snow_warehouse_size) AS snow_warehouse_size,
    MAX(dbx_warehouse_size) AS dbx_warehouse_size,
    ROUND(SUM(snow_wall_clock_seconds), 2) AS snow_wall_clock_seconds,
    ROUND(SUM(dbx_wall_clock_seconds), 2) AS dbx_wall_clock_seconds,
    ROUND(SUM(snow_total_credits), 4) AS snow_total_credits,
    ROUND(SUM(dbx_total_dbus), 4) AS dbx_total_dbus,
    ROUND(SUM(snow_total_cost), 2) AS snow_total_cost,
    ROUND(SUM(dbx_total_cost), 2) AS dbx_total_cost
FROM {{ ref('run_summary') }}
GROUP BY scenario, warehouse_tier
ORDER BY
    CASE scenario
        WHEN 'normal' THEN 1
        WHEN 'coldstart' THEN 2
        WHEN 'concurrent' THEN 3
        WHEN 'ctas' THEN 4
        ELSE 5
    END,
    warehouse_tier
