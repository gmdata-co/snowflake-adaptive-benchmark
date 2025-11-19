

-- Snowflake warehouse costs for latest runs by scenario
WITH latest_run_info AS (
    SELECT DISTINCT
        run_id,
        scenario,
        warehouse_name
    FROM "benchmark_results"."main"."int_snowflake_latest_by_scenario"
),

warehouse_costs AS (
    SELECT
        u.warehouse_name,
        SUM(u.total_credits) AS total_credits,
        SUM(u.total_credits * 3) AS total_dollars
    FROM "benchmark_results"."main"."snowflake_wh_usage" u
    INNER JOIN latest_run_info w
        ON u.warehouse_name = w.warehouse_name
    GROUP BY u.warehouse_name
)

SELECT
    w.run_id,
    w.scenario,
    w.warehouse_name,
    COALESCE(c.total_credits, 0) AS total_credits,
    COALESCE(c.total_dollars, 0) AS total_dollars
FROM latest_run_info w
LEFT JOIN warehouse_costs c
    ON w.warehouse_name = c.warehouse_name