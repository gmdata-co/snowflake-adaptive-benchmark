{{
    config(
        materialized='view'
    )
}}

-- Platform comparison for all runs (filterable by run_id, scenario, etc.)
-- Unlike platform_comparison_latest, this is not filtered to a specific run_id

WITH
snowflake_first_run AS (
    SELECT s.*
    FROM {{ ref('base_snowflake_results') }} s
    WHERE s.run_num = (
        SELECT MIN(run_num)
        FROM {{ ref('base_snowflake_results') }} sub
        WHERE sub.run_id = s.run_id
        AND sub.scenario = s.scenario
        AND sub.query_num = s.query_num
    )
),

databricks_first_run AS (
    SELECT d.*
    FROM {{ ref('base_databricks_results') }} d
    WHERE d.run_num = (
        SELECT MIN(run_num)
        FROM {{ ref('base_databricks_results') }} sub
        WHERE sub.run_id = d.run_id
        AND sub.scenario = d.scenario
        AND sub.query_num = d.query_num
    )
),

snowflake_cost AS (
    SELECT * FROM {{ ref('int_snowflake_costs') }}
),

databricks_cost AS (
    SELECT * FROM {{ ref('int_databricks_costs') }}
),

-- Get total costs per run_id
snowflake_total_cost AS (
    SELECT
        run_id,
        SUM(total_dollars) as total_cost
    FROM snowflake_cost
    GROUP BY run_id
),

databricks_total_cost AS (
    SELECT
        run_id,
        SUM(total_dollars) as total_cost
    FROM databricks_cost
    GROUP BY run_id
),

-- Get total execution time per run_id (for cost allocation)
snowflake_total_time AS (
    SELECT
        run_id,
        SUM(execution_time_sec) as total_seconds
    FROM snowflake_first_run
    WHERE error_message = ''
    GROUP BY run_id
),

databricks_total_time AS (
    SELECT
        run_id,
        SUM(execution_time_sec) as total_seconds
    FROM databricks_first_run
    WHERE error_message = ''
    GROUP BY run_id
)

-- Individual query results with cost allocation
SELECT
    COALESCE(s.run_id, d.run_id) AS run_id,
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
        WHEN s.error_message = '' AND stt.total_seconds > 0
        THEN ROUND(
            (s.execution_time_sec / stt.total_seconds)
            * stc.total_cost,
            4
        )
        ELSE NULL
    END AS snowflake_cost,
    -- Allocate Databricks cost proportionally based on execution time
    CASE
        WHEN d.error_message = '' AND dtt.total_seconds > 0
        THEN ROUND(
            (d.execution_time_sec / dtt.total_seconds)
            * dtc.total_cost,
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
FROM snowflake_first_run s
FULL OUTER JOIN databricks_first_run d
    ON s.run_id = d.run_id
    AND s.query_num = d.query_num
    AND s.scenario = d.scenario
LEFT JOIN snowflake_total_time stt ON s.run_id = stt.run_id
LEFT JOIN snowflake_total_cost stc ON s.run_id = stc.run_id
LEFT JOIN databricks_total_time dtt ON d.run_id = dtt.run_id
LEFT JOIN databricks_total_cost dtc ON d.run_id = dtc.run_id

ORDER BY run_id, scenario, query_num
