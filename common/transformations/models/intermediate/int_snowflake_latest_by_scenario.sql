{{
    config(
        materialized='view'
    )
}}

-- Get Snowflake run for each scenario, controlled by run_control table
-- When run_id = 999, use latest run. Otherwise use specified run_id.
WITH control AS (
    SELECT run_type, run_id
    FROM {{ source('main', 'run_control') }}
    WHERE run_type IN ('normal', 'coldstart')
),

-- Find latest run_id for each scenario (used when control.run_id = 999)
latest_runs AS (
    SELECT
        scenario,
        MAX(timestamp) AS latest_timestamp
    FROM {{ ref('base_snowflake_results') }}
    GROUP BY scenario
),

latest_run_ids AS (
    SELECT DISTINCT
        r.scenario,
        r.run_id
    FROM {{ ref('base_snowflake_results') }} r
    INNER JOIN latest_runs l
        ON r.scenario = l.scenario
        AND r.timestamp = l.latest_timestamp
),

-- Resolve which run_id to use: 999 means latest, otherwise use specified run_id
resolved_runs AS (
    SELECT
        c.run_type as scenario,
        CASE
            WHEN c.run_id = 999 THEN CAST(l.run_id AS INTEGER)
            ELSE c.run_id
        END as run_id
    FROM control c
    LEFT JOIN latest_run_ids l ON c.run_type = l.scenario
)

SELECT
    r.*
FROM {{ ref('base_snowflake_results') }} r
INNER JOIN resolved_runs rr
    ON r.run_id = rr.run_id
    AND r.scenario = rr.scenario
WHERE r.run_num = (
    SELECT MIN(run_num)
    FROM {{ ref('base_snowflake_results') }} sub
    WHERE sub.run_id = r.run_id
    AND sub.scenario = r.scenario
)
ORDER BY r.scenario, r.query_num
