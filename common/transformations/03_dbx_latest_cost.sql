-- Databricks warehouse costs for the latest benchmark run
-- Aggregates total DBUs consumed and total cost for the run period
CREATE OR REPLACE VIEW dbx_latest_cost AS
WITH latest_run_window AS (
    SELECT
        run_id,
        warehouse_name AS warehouse_id,
        MIN(timestamp) AS run_start,
        MAX(timestamp) AS run_end
    FROM main.databricks_results
    WHERE run_id = (
        SELECT run_id
        FROM main.databricks_results
        ORDER BY timestamp DESC
        LIMIT 1
    )
    GROUP BY run_id, warehouse_name
),
warehouse_costs AS (
    SELECT
        u.warehouse_id,
        SUM(u.usage_quantity) AS total_dbus,
        SUM(u.usage_quantity * p.price_per_unit) AS total_dollars
    FROM main.databricks_wh_usage u
    JOIN main.databricks_pricing p
        ON u.sku_name = p.sku_name
        AND u.cloud = p.cloud
    JOIN latest_run_window w
        ON u.warehouse_id = w.warehouse_id
        AND u.usage_start_time >= w.run_start
        AND u.usage_end_time <= w.run_end
    GROUP BY u.warehouse_id
)
SELECT
    w.run_id,
    w.warehouse_id,
    COALESCE(c.total_dbus, 0) AS total_dbus,
    COALESCE(c.total_dollars, 0) AS total_dollars
FROM latest_run_window w
LEFT JOIN warehouse_costs c
    ON w.warehouse_id = c.warehouse_id;
