-- Databricks Warehouse Cost Summary
-- Aggregates total DBUs consumed and costs per warehouse
CREATE OR REPLACE VIEW databricks_warehouse_cost_summary AS
SELECT
    warehouse_id,
    COUNT(*) AS usage_periods,
    MIN(usage_start_time) AS first_usage,
    MAX(usage_end_time) AS last_usage,
    SUM(dbus_consumed) AS total_dbus,
    MIN(price_per_dbu) AS price_per_dbu,
    MIN(currency_code) AS currency_code,
    SUM(cost) AS total_cost,
    sku_name,
    cloud
FROM main.databricks_warehouse_costs
GROUP BY warehouse_id, sku_name, cloud
ORDER BY total_cost DESC;
