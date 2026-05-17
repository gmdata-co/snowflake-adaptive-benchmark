{{
    config(
        materialized='view'
    )
}}

-- Headline view for the Adaptive-vs-Gen1 chart.
--
-- Grain: (run_id, scenario, warehouse_type, warehouse_size, qtm, idle_policy).
-- idle_policy is a real run-time column (wait_for_suspend | immediate_drop |
-- n_a for adaptive) that drives the dashboard tail/no-tail toggle directly,
-- replacing the old run_id->policy guesswork.
-- For each variant the user sweeps, this row holds the total wall-clock
-- duration and total Snowflake compute + cloud-services credits.
--
-- Credits come from enrich_results.py which:
--   * pulls credits_used_compute proportionally from WAREHOUSE_METERING_HISTORY,
--   * pulls credits_used_cloud_services directly from QUERY_HISTORY.
-- Both columns are populated for both gen1 and adaptive warehouses.
--
-- Cost ($) assumes a flat $2.00/credit. The visualization layer may override
-- this for what-if pricing, but a single canonical number is exposed here so
-- the chart can be plotted without further math.

WITH per_query_costs AS (
    SELECT
        run_id,
        scenario,
        warehouse_type,
        warehouse_size,
        qtm,
        COALESCE(idle_policy, 'n_a') AS idle_policy,
        SUM(COALESCE(credits_used_compute, 0)) AS total_credits_compute,
        SUM(COALESCE(credits_used_cloud_services, 0)) AS total_credits_cloud_services,
        COUNT(*) AS query_count
    FROM {{ ref('base_snowflake_results') }}
    GROUP BY run_id, scenario, warehouse_type, warehouse_size, qtm,
             COALESCE(idle_policy, 'n_a')
),

wall_clock AS (
    SELECT
        run_id,
        scenario,
        warehouse_type,
        warehouse_size,
        qtm,
        COALESCE(idle_policy, 'n_a') AS idle_policy,
        SUM(total_wall_clock_seconds) AS total_wall_clock_seconds
    FROM {{ source('main', 'run_metadata') }}
    WHERE platform = 'snowflake'
    GROUP BY run_id, scenario, warehouse_type, warehouse_size, qtm,
             COALESCE(idle_policy, 'n_a')
)

SELECT
    c.run_id,
    c.scenario,
    c.warehouse_type,
    c.warehouse_size,
    c.qtm,
    c.idle_policy,
    -- Tier ordering for chart axis: XSMALL < SMALL < MEDIUM < LARGE < XLARGE
    CASE c.warehouse_size
        WHEN 'XSMALL' THEN 1
        WHEN 'SMALL'  THEN 2
        WHEN 'MEDIUM' THEN 3
        WHEN 'LARGE'  THEN 4
        WHEN 'XLARGE' THEN 5
        ELSE 0
    END AS warehouse_tier,
    ROUND(w.total_wall_clock_seconds, 2) AS total_wall_clock_seconds,
    ROUND(c.total_credits_compute, 4)    AS total_credits_compute,
    ROUND(c.total_credits_cloud_services, 4) AS total_credits_cloud_services,
    ROUND(c.total_credits_compute + c.total_credits_cloud_services, 4) AS total_credits,
    ROUND((c.total_credits_compute + c.total_credits_cloud_services) * 2.00, 2) AS total_cost_usd,
    c.query_count
FROM per_query_costs c
LEFT JOIN wall_clock w
    ON c.run_id = w.run_id
   AND c.scenario = w.scenario
   AND c.warehouse_type = w.warehouse_type
   AND c.warehouse_size = w.warehouse_size
   AND COALESCE(c.qtm, -1) = COALESCE(w.qtm, -1)
   AND c.idle_policy = w.idle_policy
ORDER BY c.scenario, c.warehouse_type, warehouse_tier, c.qtm, c.idle_policy
