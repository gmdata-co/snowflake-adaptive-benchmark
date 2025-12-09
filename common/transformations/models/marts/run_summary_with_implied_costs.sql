{{
    config(
        materialized='view'
    )
}}

-- Extends run_summary with implied credits/cost for sense-checking Snowflake costs

SELECT
    *,
    -- Credits per hour by warehouse size: MEDIUM=4, LARGE=8, XLARGE=16
    ROUND(
        (snow_wall_clock_seconds / 3600.0) *
        CASE snow_warehouse_size
            WHEN 'MEDIUM' THEN 4
            WHEN 'LARGE' THEN 8
            WHEN 'XLARGE' THEN 16
            ELSE 0
        END,
        4
    ) AS snow_implied_credits,
    ROUND(
        (snow_wall_clock_seconds / 3600.0) *
        CASE snow_warehouse_size
            WHEN 'MEDIUM' THEN 4
            WHEN 'LARGE' THEN 8
            WHEN 'XLARGE' THEN 16
            ELSE 0
        END * 2,
        4
    ) AS snow_implied_cost
FROM {{ ref('run_summary') }}
