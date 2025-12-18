{{
    config(
        materialized='view'
    )
}}

-- Pivoted run metadata with wall clock times, costs by platform and warehouse size
-- Uses warehouse_tier for cross-platform comparison:
--   Tier 0: Snowflake Small (standalone)
--   Tier 1: DBX Small  | Snowflake Medium
--   Tier 2: DBX Medium | Snowflake Large
--   Tier 3: DBX Large  | Snowflake XLarge
--   Tier 4: DBX XLarge (standalone)

WITH
-- Snowflake run metadata with tier mapping
snowflake_metadata AS (
    SELECT
        run_id,
        scenario,
        warehouse_size,
        warehouse_name,
        total_wall_clock_seconds,
        -- Map to tier: SMALL=0, MEDIUM=1, LARGE=2, XLARGE=3
        CASE warehouse_size
            WHEN 'SMALL' THEN 0
            WHEN 'MEDIUM' THEN 1
            WHEN 'LARGE' THEN 2
            WHEN 'XLARGE' THEN 3
            ELSE -1  -- Unknown sizes
        END AS warehouse_tier
    FROM {{ source('main', 'run_metadata') }}
    WHERE platform = 'snowflake'
    {% if var('run_ids', []) | length > 0 %}
        AND run_id IN ('{{ var('run_ids') | join("', '") }}')
    {% endif %}
),

-- Databricks run metadata with tier mapping
databricks_metadata AS (
    SELECT
        run_id,
        scenario,
        warehouse_size,
        warehouse_name,
        total_wall_clock_seconds,
        -- Map to tier: SMALL=1, MEDIUM=2, LARGE=3, XLARGE=4
        CASE warehouse_size
            WHEN 'SMALL' THEN 1
            WHEN 'MEDIUM' THEN 2
            WHEN 'LARGE' THEN 3
            WHEN 'XLARGE' THEN 4
            ELSE -1  -- Unknown sizes
        END AS warehouse_tier
    FROM {{ source('main', 'run_metadata') }}
    WHERE platform = 'databricks'
    {% if var('run_ids', []) | length > 0 %}
        AND run_id IN ('{{ var('run_ids') | join("', '") }}')
    {% endif %}
),

-- Calculate Snowflake costs from usage table
snowflake_costs AS (
    SELECT
        sm.run_id,
        sm.scenario,
        sm.warehouse_tier,
        SUM(u.total_credits) AS total_credits,
        SUM(u.total_credits) * 2 AS total_dollars
    FROM snowflake_metadata sm
    INNER JOIN {{ source('main', 'snowflake_wh_usage') }} u
        ON sm.warehouse_name = u.warehouse_name
    GROUP BY sm.run_id, sm.scenario, sm.warehouse_tier
),

-- Calculate Databricks costs from usage table
databricks_costs AS (
    SELECT
        dm.run_id,
        dm.scenario,
        dm.warehouse_tier,
        SUM(u.usage_quantity) AS total_dbus,
        SUM(u.usage_quantity * p.price_per_unit) AS total_dollars
    FROM databricks_metadata dm
    INNER JOIN {{ source('main', 'databricks_wh_usage') }} u
        ON dm.warehouse_name = u.warehouse_id
    INNER JOIN {{ source('main', 'databricks_pricing') }} p
        ON u.sku_name = p.sku_name
        AND u.cloud = p.cloud
    GROUP BY dm.run_id, dm.scenario, dm.warehouse_tier
)

SELECT
    COALESCE(s.run_id, d.run_id) AS run_id,
    COALESCE(s.scenario, d.scenario) AS scenario,
    COALESCE(s.warehouse_tier, d.warehouse_tier) AS warehouse_tier,
    s.warehouse_size AS snow_warehouse_size,
    d.warehouse_size AS dbx_warehouse_size,
    ROUND(s.total_wall_clock_seconds, 2) AS snow_wall_clock_seconds,
    ROUND(d.total_wall_clock_seconds, 2) AS dbx_wall_clock_seconds,
    ROUND(COALESCE(sc.total_credits, 0), 4) AS snow_total_credits,
    ROUND(COALESCE(dc.total_dbus, 0), 4) AS dbx_total_dbus,
    ROUND(COALESCE(sc.total_dollars, 0), 2) AS snow_total_cost,
    ROUND(COALESCE(dc.total_dollars, 0), 2) AS dbx_total_cost,
    ROUND(COALESCE(sc.total_dollars, 0) - COALESCE(dc.total_dollars, 0), 2) AS cost_diff
FROM snowflake_metadata s
FULL OUTER JOIN databricks_metadata d
    ON s.run_id = d.run_id
    AND s.scenario = d.scenario
    AND s.warehouse_tier = d.warehouse_tier
LEFT JOIN snowflake_costs sc
    ON s.run_id = sc.run_id
    AND s.scenario = sc.scenario
    AND s.warehouse_tier = sc.warehouse_tier
LEFT JOIN databricks_costs dc
    ON d.run_id = dc.run_id
    AND d.scenario = dc.scenario
    AND d.warehouse_tier = dc.warehouse_tier
ORDER BY run_id, scenario, warehouse_tier
