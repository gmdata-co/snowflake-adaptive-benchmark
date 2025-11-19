

-- Databricks warehouse costs for latest runs by scenario
WITH latest_run_info AS (
    SELECT DISTINCT
        run_id,
        scenario,
        warehouse_name AS warehouse_id
    FROM "benchmark_results"."main"."int_databricks_latest_by_scenario"
),

warehouse_costs AS (
    SELECT
        u.warehouse_id,
        SUM(u.usage_quantity) AS total_dbus,
        SUM(u.usage_quantity * p.price_per_unit) AS total_dollars
    FROM "benchmark_results"."main"."databricks_wh_usage" u
    JOIN "benchmark_results"."main"."databricks_pricing" p
        ON u.sku_name = p.sku_name
        AND u.cloud = p.cloud
    INNER JOIN latest_run_info w
        ON u.warehouse_id = w.warehouse_id
    GROUP BY u.warehouse_id
)

SELECT
    w.run_id,
    w.scenario,
    w.warehouse_id,
    COALESCE(c.total_dbus, 0) AS total_dbus,
    COALESCE(c.total_dollars, 0) AS total_dollars
FROM latest_run_info w
LEFT JOIN warehouse_costs c
    ON w.warehouse_id = c.warehouse_id