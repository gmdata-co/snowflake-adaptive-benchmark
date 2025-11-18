-- Databricks Warehouse Usage with Cost Calculations
-- Enriches warehouse usage data with pricing to show total costs
CREATE OR REPLACE VIEW databricks_warehouse_costs AS
SELECT
    u.warehouse_id,
    u.usage_date,
    u.usage_start_time,
    u.usage_end_time,
    u.usage_quantity AS dbus_consumed,
    u.usage_unit,
    u.billing_origin_product,
    u.sku_name,
    u.cloud,
    p.price_per_unit AS price_per_dbu,
    p.currency_code,
    (u.usage_quantity * p.price_per_unit) AS cost,
    u.loaded_at
FROM main.databricks_wh_usage u
JOIN main.databricks_pricing p
    ON u.sku_name = p.sku_name
    AND u.cloud = p.cloud
ORDER BY u.usage_start_time, u.warehouse_id;
