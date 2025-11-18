-- Platform comparison with dollar costs for both Snowflake and Databricks
-- Allocates warehouse costs to individual queries based on proportional execution time
CREATE OR REPLACE VIEW comparison_dollars_both AS

WITH
-- Get total warehouse cost for Databricks
databricks_total_cost AS (
    SELECT SUM(total_cost) as total_cost
    FROM main.databricks_warehouse_cost_summary
),

-- Get total execution time for all Databricks queries (to use as denominator)
databricks_total_time AS (
    SELECT SUM(execution_time_sec) as total_seconds
    FROM main.latest_databricks
    WHERE error_message = ''
),

-- Get total warehouse cost for Snowflake
snowflake_total_cost AS (
    SELECT SUM(total_cost) as total_cost
    FROM main.snowflake_warehouse_cost_summary
),

-- Get total execution time for all Snowflake queries (to use as denominator)
snowflake_total_time AS (
    SELECT SUM(execution_time_sec) as total_seconds
    FROM main.latest_snowflake
    WHERE error_message = ''
),

-- Individual query results with cost allocation
query_costs AS (
    SELECT
        COALESCE(s.query_num, d.query_num) AS query_num,
        CASE
            WHEN s.error_message = '' THEN ROUND(s.execution_time_sec, 1)
            ELSE NULL
        END AS snowflake_seconds,
        CASE
            WHEN d.error_message = '' THEN ROUND(d.execution_time_sec, 1)
            ELSE NULL
        END AS dbx_seconds,
        -- Allocate Snowflake cost proportionally based on execution time
        CASE
            WHEN s.error_message = '' AND (SELECT total_seconds FROM snowflake_total_time) > 0
            THEN ROUND(
                (s.execution_time_sec / (SELECT total_seconds FROM snowflake_total_time))
                * (SELECT total_cost FROM snowflake_total_cost),
                4
            )
            ELSE NULL
        END AS snowflake_cost,
        -- Allocate Databricks cost proportionally based on execution time
        CASE
            WHEN d.error_message = '' AND (SELECT total_seconds FROM databricks_total_time) > 0
            THEN ROUND(
                (d.execution_time_sec / (SELECT total_seconds FROM databricks_total_time))
                * (SELECT total_cost FROM databricks_total_cost),
                4
            )
            ELSE NULL
        END AS dbx_cost,
        CASE
            WHEN s.error_message = '' THEN s.rows_produced
            ELSE NULL
        END AS row_count,
        CASE
            WHEN s.error_message = '' AND d.error_message = '' THEN 'success'
            WHEN s.error_message != '' AND d.error_message = '' THEN 'snowflake_error'
            WHEN s.error_message = '' AND d.error_message != '' THEN 'databricks_error'
            WHEN s.error_message != '' AND d.error_message != '' THEN 'both_error'
            ELSE 'unknown'
        END AS status
    FROM main.latest_snowflake s
    FULL OUTER JOIN main.latest_databricks d
        ON s.query_num = d.query_num
)

-- Individual queries
SELECT * FROM query_costs

UNION ALL

-- Grand total row
SELECT
    999999 AS query_num,
    ROUND(SUM(snowflake_seconds), 1) AS snowflake_seconds,
    ROUND(SUM(dbx_seconds), 1) AS dbx_seconds,
    ROUND(SUM(snowflake_cost), 4) AS snowflake_cost,
    ROUND(SUM(dbx_cost), 4) AS dbx_cost,
    SUM(row_count) AS row_count,
    'TOTAL' AS status
FROM query_costs

ORDER BY query_num;
