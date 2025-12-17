{{
    config(
        materialized='view'
    )
}}

-- CTAS Benchmark Summary: Performance and costs by variant
-- Compares write performance across different data shapes

WITH
-- Snowflake CTAS results
snowflake_ctas AS (
    SELECT
        run_id,
        warehouse_size,
        ctas_variant,
        execution_time_sec AS duration_seconds,
        query_id,
        timestamp,
        rows_produced,
        credits_used_compute,
        credits_used_cloud_services,
        (COALESCE(credits_used_compute, 0) + COALESCE(credits_used_cloud_services, 0)) * 2 AS cost_dollars
    FROM {{ source('main', 'snowflake_results') }}
    WHERE scenario = 'ctas'
        AND ctas_variant IS NOT NULL
),

-- Databricks CTAS results
databricks_ctas AS (
    SELECT
        run_id,
        warehouse_size,
        ctas_variant,
        execution_time_sec AS duration_seconds,
        query_id,
        timestamp,
        rows_produced,
        credits_used_compute AS dbus_used,
        credits_used_compute * 0.22 AS cost_dollars
    FROM {{ source('main', 'databricks_results') }}
    WHERE scenario = 'ctas'
        AND ctas_variant IS NOT NULL
),

-- Unified warehouse tier mapping
unified AS (
    SELECT
        COALESCE(s.run_id, d.run_id) AS run_id,
        COALESCE(s.ctas_variant, d.ctas_variant) AS ctas_variant,
        -- Map to unified tier
        CASE
            WHEN s.warehouse_size = 'MEDIUM' OR d.warehouse_size = 'SMALL' THEN 1
            WHEN s.warehouse_size = 'LARGE' OR d.warehouse_size = 'MEDIUM' THEN 2
            WHEN s.warehouse_size = 'XLARGE' OR d.warehouse_size = 'LARGE' THEN 3
            ELSE 0
        END AS unified_size,
        s.warehouse_size AS snow_warehouse_size,
        d.warehouse_size AS dbx_warehouse_size,
        s.duration_seconds AS snow_duration_seconds,
        d.duration_seconds AS dbx_duration_seconds,
        s.query_id AS snow_query_id,
        d.query_id AS dbx_query_id,
        s.timestamp AS snow_timestamp,
        d.timestamp AS dbx_timestamp,
        s.rows_produced AS snow_rows_produced,
        d.rows_produced AS dbx_rows_produced,
        s.cost_dollars AS snow_cost_dollars,
        d.cost_dollars AS dbx_cost_dollars,
        s.credits_used_compute AS snow_credits_compute,
        s.credits_used_cloud_services AS snow_credits_cloud_services,
        d.dbus_used AS dbx_dbus_used
    FROM snowflake_ctas s
    FULL OUTER JOIN databricks_ctas d
        ON s.run_id = d.run_id
        AND s.ctas_variant = d.ctas_variant
        AND (
            (s.warehouse_size = 'MEDIUM' AND d.warehouse_size = 'SMALL') OR
            (s.warehouse_size = 'LARGE' AND d.warehouse_size = 'MEDIUM') OR
            (s.warehouse_size = 'XLARGE' AND d.warehouse_size = 'LARGE')
        )
)

SELECT
    run_id,
    ctas_variant,
    unified_size,
    snow_warehouse_size,
    dbx_warehouse_size,
    ROUND(snow_duration_seconds, 2) AS snow_duration_seconds,
    ROUND(dbx_duration_seconds, 2) AS dbx_duration_seconds,
    ROUND(snow_duration_seconds - dbx_duration_seconds, 2) AS duration_diff_seconds,
    ROUND((snow_duration_seconds / NULLIF(dbx_duration_seconds, 0)), 2) AS snow_to_dbx_ratio,
    snow_query_id,
    dbx_query_id,
    snow_timestamp,
    dbx_timestamp,
    snow_rows_produced,
    dbx_rows_produced,
    ROUND(COALESCE(snow_cost_dollars, 0), 2) AS snow_cost_dollars,
    ROUND(COALESCE(dbx_cost_dollars, 0), 2) AS dbx_cost_dollars,
    ROUND(COALESCE(snow_cost_dollars, 0) - COALESCE(dbx_cost_dollars, 0), 2) AS cost_diff_dollars,
    ROUND(snow_credits_compute, 2) AS snow_credits_compute,
    ROUND(snow_credits_cloud_services, 2) AS snow_credits_cloud_services,
    ROUND(dbx_dbus_used, 2) AS dbx_dbus_used,
    -- Variant metadata
    CASE ctas_variant
        WHEN 'narrow_tall' THEN '6B rows × 4 cols'
        WHEN 'standard_tall' THEN '6B rows × 16 cols'
        WHEN 'medium_wide' THEN '1.5B rows × 30 cols'
        WHEN 'very_wide' THEN '6B rows × 59 cols'
        WHEN 'filtered' THEN '2B rows × 16 cols'
        ELSE 'Unknown'
    END AS variant_description
FROM unified
WHERE ctas_variant IS NOT NULL
ORDER BY run_id, ctas_variant, unified_size
