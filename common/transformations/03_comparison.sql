-- Platform comparison: Snowflake vs Databricks
-- Shows execution time in seconds for each query in the latest runs
-- Includes a grand total row at the bottom
CREATE OR REPLACE VIEW platform_comparison AS

-- Individual query results
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

UNION ALL

-- Grand total row
SELECT
    999999 AS query_num,  -- Large number to sort to bottom
    ROUND(SUM(CASE WHEN s.error_message = '' THEN s.execution_time_sec ELSE NULL END), 1) AS snowflake_seconds,
    ROUND(SUM(CASE WHEN d.error_message = '' THEN d.execution_time_sec ELSE NULL END), 1) AS dbx_seconds,
    SUM(CASE WHEN s.error_message = '' THEN s.rows_produced ELSE NULL END) AS row_count,
    'TOTAL' AS status
FROM main.latest_snowflake s
FULL OUTER JOIN main.latest_databricks d
    ON s.query_num = d.query_num

ORDER BY query_num;
