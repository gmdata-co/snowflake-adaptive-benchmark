{{
    config(
        materialized='view'
    )
}}

-- Run summary by warehouse size with wall clock times and costs
-- Uses warehouse_tier for cross-platform comparison (since sizes differ)
-- Tier 1 = smallest, Tier 2 = medium, Tier 3 = largest

WITH
-- Snowflake run metadata
snowflake_metadata AS (
    SELECT
        run_id,
        scenario,
        warehouse_size,
        warehouse_name,
        total_wall_clock_seconds,
        -- Map to tier: MEDIUM=1, LARGE=2, XLARGE=3
        CASE warehouse_size
            WHEN 'MEDIUM' THEN 1
            WHEN 'LARGE' THEN 2
            WHEN 'XLARGE' THEN 3
            ELSE 0
        END AS warehouse_tier
    FROM {{ source('main', 'run_metadata') }}
    WHERE platform = 'snowflake'
),

-- Databricks run metadata
databricks_metadata AS (
    SELECT
        run_id,
        scenario,
        warehouse_size,
        warehouse_name,
        total_wall_clock_seconds,
        -- Map to tier: SMALL=1, MEDIUM=2, LARGE=3
        CASE warehouse_size
            WHEN 'SMALL' THEN 1
            WHEN 'MEDIUM' THEN 2
            WHEN 'LARGE' THEN 3
            ELSE 0
        END AS warehouse_tier
    FROM {{ source('main', 'run_metadata') }}
    WHERE platform = 'databricks'
),

-- Calculate Snowflake costs from usage table (by warehouse_name)
snowflake_costs AS (
    SELECT
        sm.run_id,
        sm.scenario,
        sm.warehouse_size,
        SUM(u.total_credits) * 3 AS total_dollars
    FROM snowflake_metadata sm
    INNER JOIN {{ source('main', 'snowflake_wh_usage') }} u
        ON sm.warehouse_name = u.warehouse_name
    GROUP BY sm.run_id, sm.scenario, sm.warehouse_size
),

-- Calculate Databricks costs from usage table (by warehouse_id)
databricks_costs AS (
    SELECT
        dm.run_id,
        dm.scenario,
        dm.warehouse_size,
        SUM(u.usage_quantity * p.price_per_unit) AS total_dollars
    FROM databricks_metadata dm
    INNER JOIN {{ source('main', 'databricks_wh_usage') }} u
        ON dm.warehouse_name = u.warehouse_id
    INNER JOIN {{ source('main', 'databricks_pricing') }} p
        ON u.sku_name = p.sku_name
        AND u.cloud = p.cloud
    GROUP BY dm.run_id, dm.scenario, dm.warehouse_size
)

SELECT
    COALESCE(s.run_id, d.run_id) AS run_id,
    COALESCE(s.scenario, d.scenario) AS scenario,
    COALESCE(s.warehouse_tier, d.warehouse_tier) AS warehouse_tier,
    s.warehouse_size AS snow_warehouse_size,
    d.warehouse_size AS dbx_warehouse_size,
    s.total_wall_clock_seconds AS snow_wall_clock_seconds,
    d.total_wall_clock_seconds AS dbx_wall_clock_seconds,
    COALESCE(sc.total_dollars, 0) AS snow_total_cost,
    COALESCE(dc.total_dollars, 0) AS dbx_total_cost
FROM snowflake_metadata s
FULL OUTER JOIN databricks_metadata d
    ON s.run_id = d.run_id
    AND s.scenario = d.scenario
    AND s.warehouse_tier = d.warehouse_tier
LEFT JOIN snowflake_costs sc
    ON s.run_id = sc.run_id
    AND s.scenario = sc.scenario
    AND s.warehouse_size = sc.warehouse_size
LEFT JOIN databricks_costs dc
    ON d.run_id = dc.run_id
    AND d.scenario = dc.scenario
    AND d.warehouse_size = dc.warehouse_size
ORDER BY run_id, scenario, warehouse_tier
