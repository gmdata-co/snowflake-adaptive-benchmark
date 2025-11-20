{{
    config(
        materialized='view'
    )
}}

-- Platform comparison for latest run_id (all scenarios combined)
-- Controlled by run_control table: when run_id = 999, use latest. Otherwise use specified run_id.
WITH
control AS (
    SELECT run_id
    FROM {{ source('main', 'run_control') }}
    WHERE run_type = 'latest'
),

-- Find overall latest run_id (used when control.run_id = 999)
latest_run_from_timestamp AS (
    SELECT
        run_id,
        MAX(timestamp) AS latest_timestamp
    FROM {{ ref('base_snowflake_results') }}
    GROUP BY run_id
    ORDER BY latest_timestamp DESC
    LIMIT 1
),

-- Resolve which run_id to use
latest_run AS (
    SELECT
        CASE
            WHEN c.run_id = 999 THEN CAST(l.run_id AS INTEGER)
            ELSE c.run_id
        END as run_id
    FROM control c
    CROSS JOIN latest_run_from_timestamp l
),

snowflake_latest AS (
    SELECT s.*
    FROM {{ ref('base_snowflake_results') }} s
    INNER JOIN latest_run l ON s.run_id = l.run_id
    WHERE s.run_num = (
        SELECT MIN(run_num)
        FROM {{ ref('base_snowflake_results') }} sub
        WHERE sub.run_id = s.run_id
        AND sub.scenario = s.scenario
        AND sub.query_num = s.query_num
    )
),

databricks_latest AS (
    SELECT d.*
    FROM {{ ref('base_databricks_results') }} d
    INNER JOIN latest_run l ON d.run_id = l.run_id
    WHERE d.run_num = (
        SELECT MIN(run_num)
        FROM {{ ref('base_databricks_results') }} sub
        WHERE sub.run_id = d.run_id
        AND sub.scenario = d.scenario
        AND sub.query_num = d.query_num
    )
),

snowflake_cost AS (
    SELECT c.*
    FROM {{ ref('int_snowflake_costs') }} c
    INNER JOIN latest_run l ON c.run_id = l.run_id
),

databricks_cost AS (
    SELECT c.*
    FROM {{ ref('int_databricks_costs') }} c
    INNER JOIN latest_run l ON c.run_id = l.run_id
),

-- Get total costs (across all scenarios)
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
    FROM snowflake_latest
    WHERE error_message = ''
),

databricks_total_time AS (
    SELECT
        SUM(execution_time_sec) as total_seconds
    FROM databricks_latest
    WHERE error_message = ''
),

-- Individual query results with cost allocation and scenario
query_costs AS (
    SELECT
        COALESCE(s.scenario, d.scenario) AS scenario,
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
    FROM snowflake_latest s
    FULL OUTER JOIN databricks_latest d
        ON s.query_num = d.query_num
        AND s.scenario = d.scenario
)

-- Individual queries
SELECT * FROM query_costs

UNION ALL

-- Grand total row
SELECT
    'TOTAL' AS scenario,
    999999 AS query_num,
    ROUND(SUM(snowflake_seconds), 1) AS snowflake_seconds,
    ROUND(SUM(dbx_seconds), 1) AS dbx_seconds,
    ROUND(SUM(snowflake_cost), 4) AS snowflake_cost,
    ROUND(SUM(dbx_cost), 4) AS dbx_cost,
    SUM(row_count) AS row_count,
    'TOTAL' AS status
FROM query_costs

ORDER BY scenario, query_num
