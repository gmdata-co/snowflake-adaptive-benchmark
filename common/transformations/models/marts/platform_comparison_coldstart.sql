{{
    config(
        materialized='view'
    )
}}

-- Platform comparison for latest COLDSTART scenario run
WITH
snowflake_coldstart AS (
    SELECT *
    FROM {{ ref('int_snowflake_latest_by_scenario') }}
    WHERE scenario IN ('coldstart', 'cold_start')  -- Handle both old and new naming
),

databricks_coldstart AS (
    SELECT *
    FROM {{ ref('int_databricks_latest_by_scenario') }}
    WHERE scenario IN ('coldstart', 'cold_start')  -- Handle both old and new naming
),

snowflake_cost AS (
    SELECT *
    FROM {{ ref('int_snowflake_costs') }}
    WHERE scenario IN ('coldstart', 'cold_start')  -- Handle both old and new naming
),

databricks_cost AS (
    SELECT *
    FROM {{ ref('int_databricks_costs') }}
    WHERE scenario IN ('coldstart', 'cold_start')  -- Handle both old and new naming
),

-- Get total costs
snowflake_total_cost AS (
    SELECT
        SUM(total_dollars) as total_cost
    FROM snowflake_cost
),

databricks_total_cost AS (
    SELECT
        SUM(total_dollars) as total_cost
    FROM databricks_cost
),

-- Get total execution time (for cost allocation)
snowflake_total_time AS (
    SELECT
        SUM(execution_time_sec) as total_seconds
    FROM snowflake_coldstart
    WHERE error_message = ''
),

databricks_total_time AS (
    SELECT
        SUM(execution_time_sec) as total_seconds
    FROM databricks_coldstart
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
    FROM snowflake_coldstart s
    FULL OUTER JOIN databricks_coldstart d
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

ORDER BY query_num
