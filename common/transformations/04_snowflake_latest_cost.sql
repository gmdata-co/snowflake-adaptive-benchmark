-- Snowflake warehouse costs for the latest benchmark run
-- Aggregates total credits consumed and total cost for the specific warehouse used
-- Uses $3/credit pricing
CREATE OR REPLACE VIEW snowflake_latest_cost AS
WITH latest_run_info AS (
    SELECT
        run_id,
        warehouse_name
    FROM main.snowflake_results
    WHERE run_id = (
        SELECT run_id
        FROM main.snowflake_results
        ORDER BY timestamp DESC
        LIMIT 1
    )
    GROUP BY run_id, warehouse_name
),
warehouse_costs AS (
    SELECT
        u.warehouse_name,
        SUM(u.total_credits) AS total_credits,
        SUM(u.total_credits * 3) AS total_dollars
    FROM main.snowflake_wh_usage u
    JOIN latest_run_info w
        ON u.warehouse_name = w.warehouse_name
    GROUP BY u.warehouse_name
)
SELECT
    w.run_id,
    w.warehouse_name,
    COALESCE(c.total_credits, 0) AS total_credits,
    COALESCE(c.total_dollars, 0) AS total_dollars
FROM latest_run_info w
LEFT JOIN warehouse_costs c
    ON w.warehouse_name = c.warehouse_name;
