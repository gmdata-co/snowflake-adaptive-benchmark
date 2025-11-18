-- Snowflake warehouse costs for the latest benchmark run
-- Aggregates total credits consumed and total cost for the run period
-- Uses $3/credit pricing
CREATE OR REPLACE VIEW snowflake_latest_cost AS
WITH latest_run_window AS (
    SELECT
        run_id,
        warehouse_name,
        MIN(timestamp) AS run_start,
        MAX(timestamp) AS run_end
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
    JOIN latest_run_window w
        ON u.warehouse_name = w.warehouse_name
        AND u.start_time >= w.run_start
        AND u.end_time <= w.run_end
    GROUP BY u.warehouse_name
)
SELECT
    w.run_id,
    w.warehouse_name,
    COALESCE(c.total_credits, 0) AS total_credits,
    COALESCE(c.total_dollars, 0) AS total_dollars
FROM latest_run_window w
LEFT JOIN warehouse_costs c
    ON w.warehouse_name = c.warehouse_name;
