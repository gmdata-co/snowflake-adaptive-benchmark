-- Snowflake Warehouse Cost Summary
-- Aggregates total credits consumed and costs per warehouse
CREATE OR REPLACE VIEW snowflake_warehouse_cost_summary AS
SELECT
    warehouse_name,
    COUNT(*) AS usage_periods,
    MIN(start_time) AS first_usage,
    MAX(end_time) AS last_usage,
    SUM(total_credits) AS total_credits,
    SUM(compute_credits) AS compute_credits,
    SUM(cloud_services_credits) AS cloud_services_credits,
    SUM(cost) AS total_cost
FROM main.snowflake_warehouse_costs
GROUP BY warehouse_name
ORDER BY total_cost DESC;
