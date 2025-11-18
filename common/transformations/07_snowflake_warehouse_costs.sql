-- Snowflake Warehouse Usage with Cost Calculations
-- Enriches warehouse usage data with $3/credit pricing to show total costs
CREATE OR REPLACE VIEW snowflake_warehouse_costs AS
SELECT
    warehouse_name,
    start_time,
    end_time,
    total_credits,
    compute_credits,
    cloud_services_credits,
    (total_credits * 3) AS cost,
    loaded_at
FROM main.snowflake_wh_usage
ORDER BY start_time, warehouse_name;
