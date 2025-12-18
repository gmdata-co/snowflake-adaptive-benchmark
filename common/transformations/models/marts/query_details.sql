{{
    config(
        materialized='view'
    )
}}

-- Query-level details with category metadata for visualization
-- Uses same run_id filtering as run_summary.sql via dbt variables

WITH
-- Snowflake results filtered by run_ids with tier mapping
snowflake_filtered AS (
    SELECT
        run_id,
        scenario,
        warehouse_size,
        warehouse_name,
        query_num,
        run_num,
        run_type,
        execution_time_sec,
        rows_produced,
        error_message,
        ctas_variant,
        -- Map to tier: SMALL=0, MEDIUM=1, LARGE=2, XLARGE=3
        CASE warehouse_size
            WHEN 'SMALL' THEN 0
            WHEN 'MEDIUM' THEN 1
            WHEN 'LARGE' THEN 2
            WHEN 'XLARGE' THEN 3
            ELSE -1
        END AS warehouse_tier
    FROM {{ ref('base_snowflake_results') }}
    {% if var('run_ids', []) | length > 0 %}
        WHERE run_id IN ('{{ var('run_ids') | join("', '") }}')
    {% endif %}
),

-- Databricks results filtered by run_ids with tier mapping
databricks_filtered AS (
    SELECT
        run_id,
        scenario,
        warehouse_size,
        warehouse_name,
        query_num,
        run_num,
        run_type,
        execution_time_sec,
        rows_produced,
        error_message,
        ctas_variant,
        -- Map to tier: SMALL=1, MEDIUM=2, LARGE=3, XLARGE=4
        CASE warehouse_size
            WHEN 'SMALL' THEN 1
            WHEN 'MEDIUM' THEN 2
            WHEN 'LARGE' THEN 3
            WHEN 'XLARGE' THEN 4
            ELSE -1
        END AS warehouse_tier
    FROM {{ ref('base_databricks_results') }}
    {% if var('run_ids', []) | length > 0 %}
        WHERE run_id IN ('{{ var('run_ids') | join("', '") }}')
    {% endif %}
),

-- Take first run (cold start) for each query in each scenario/tier - Snowflake
snowflake_first AS (
    SELECT *
    FROM snowflake_filtered s
    WHERE s.run_num = (
        SELECT MIN(run_num)
        FROM snowflake_filtered sub
        WHERE sub.run_id = s.run_id
        AND sub.scenario = s.scenario
        AND sub.warehouse_tier = s.warehouse_tier
        AND sub.query_num = s.query_num
        AND COALESCE(sub.ctas_variant, '') = COALESCE(s.ctas_variant, '')
    )
),

-- Take first run (cold start) for each query in each scenario/tier - Databricks
databricks_first AS (
    SELECT *
    FROM databricks_filtered d
    WHERE d.run_num = (
        SELECT MIN(run_num)
        FROM databricks_filtered sub
        WHERE sub.run_id = d.run_id
        AND sub.scenario = d.scenario
        AND sub.warehouse_tier = d.warehouse_tier
        AND sub.query_num = d.query_num
        AND COALESCE(sub.ctas_variant, '') = COALESCE(d.ctas_variant, '')
    )
),

-- Total execution time by scenario/tier for proportional cost allocation
snowflake_totals AS (
    SELECT
        scenario,
        warehouse_tier,
        SUM(execution_time_sec) AS total_exec_time
    FROM snowflake_first
    WHERE execution_time_sec IS NOT NULL
    GROUP BY scenario, warehouse_tier
),

databricks_totals AS (
    SELECT
        scenario,
        warehouse_tier,
        SUM(execution_time_sec) AS total_exec_time
    FROM databricks_first
    WHERE execution_time_sec IS NOT NULL
    GROUP BY scenario, warehouse_tier
),

-- Combine platforms with category metadata from seeds
combined AS (
    SELECT
        COALESCE(s.run_id, d.run_id) AS run_id,
        COALESCE(s.scenario, d.scenario) AS scenario,
        COALESCE(s.warehouse_tier, d.warehouse_tier) AS warehouse_tier,
        COALESCE(s.query_num, d.query_num) AS query_num,
        COALESCE(s.ctas_variant, d.ctas_variant) AS ctas_variant,

        -- Query identifier (Q01, Q02, ... or CTAS/DML variant name in uppercase)
        CASE
            WHEN COALESCE(s.ctas_variant, d.ctas_variant) IS NOT NULL
                THEN UPPER(COALESCE(s.ctas_variant, d.ctas_variant))
            ELSE 'Q' || LPAD(CAST(COALESCE(s.query_num, d.query_num) AS VARCHAR), 2, '0')
        END AS query_id_display,

        -- Category/type from seeds
        CASE
            WHEN COALESCE(s.scenario, d.scenario) = 'dml' THEN 'DML'
            WHEN COALESCE(s.ctas_variant, d.ctas_variant) IS NOT NULL THEN 'CTAS'
            ELSE COALESCE(qc.query_type, 'TPC-H')
        END AS query_type,

        CASE
            WHEN COALESCE(s.scenario, d.scenario) = 'dml'
                THEN 'DML Operation'
            WHEN COALESCE(s.ctas_variant, d.ctas_variant) IS NOT NULL
                THEN 'CTAS Variant'
            ELSE COALESCE(qc.category, 'Unknown')
        END AS query_category,

        CASE
            WHEN COALESCE(s.scenario, d.scenario) = 'dml'
                THEN COALESCE(dv.variant_description, COALESCE(s.ctas_variant, d.ctas_variant))
            WHEN COALESCE(s.ctas_variant, d.ctas_variant) IS NOT NULL
                THEN COALESCE(cv.variant_description, COALESCE(s.ctas_variant, d.ctas_variant))
            ELSE COALESCE(qc.description, '')
        END AS query_description,

        -- SQL snippet from seeds
        CASE
            WHEN COALESCE(s.scenario, d.scenario) = 'dml'
                THEN COALESCE(dv.sql_snippet, '')
            WHEN COALESCE(s.ctas_variant, d.ctas_variant) IS NOT NULL
                THEN COALESCE(cv.sql_snippet, '')
            ELSE COALESCE(qc.sql_snippet, '')
        END AS sql_snippet,

        -- Snowflake metrics
        s.warehouse_size AS snow_warehouse_size,
        s.warehouse_name AS snow_warehouse_name,
        ROUND(s.execution_time_sec, 2) AS snow_execution_sec,
        s.rows_produced AS snow_rows_produced,
        s.error_message AS snow_error,

        -- Databricks metrics
        d.warehouse_size AS dbx_warehouse_size,
        d.warehouse_name AS dbx_warehouse_name,
        ROUND(d.execution_time_sec, 2) AS dbx_execution_sec,
        d.rows_produced AS dbx_rows_produced,
        d.error_message AS dbx_error,

        -- Total execution times for proportional cost allocation
        st.total_exec_time AS snow_total_exec_time,
        dt.total_exec_time AS dbx_total_exec_time

    FROM snowflake_first s
    FULL OUTER JOIN databricks_first d
        ON s.scenario = d.scenario
        AND s.warehouse_tier = d.warehouse_tier
        AND s.query_num = d.query_num
        AND COALESCE(s.ctas_variant, '') = COALESCE(d.ctas_variant, '')
    LEFT JOIN {{ ref('query_categories') }} qc
        ON qc.query_num = COALESCE(s.query_num, d.query_num)
    LEFT JOIN {{ ref('ctas_variants') }} cv
        ON cv.ctas_variant = COALESCE(s.ctas_variant, d.ctas_variant)
    LEFT JOIN {{ ref('dml_variants') }} dv
        ON dv.dml_variant = COALESCE(s.ctas_variant, d.ctas_variant)
        AND COALESCE(s.scenario, d.scenario) = 'dml'
    LEFT JOIN snowflake_totals st
        ON st.scenario = COALESCE(s.scenario, d.scenario)
        AND st.warehouse_tier = COALESCE(s.warehouse_tier, d.warehouse_tier)
    LEFT JOIN databricks_totals dt
        ON dt.scenario = COALESCE(s.scenario, d.scenario)
        AND dt.warehouse_tier = COALESCE(s.warehouse_tier, d.warehouse_tier)
)

SELECT * FROM combined
ORDER BY
    CASE scenario
        WHEN 'normal' THEN 1
        WHEN 'coldstart' THEN 2
        WHEN 'concurrent' THEN 3
        WHEN 'ctas' THEN 4
        WHEN 'dml' THEN 5
        ELSE 6
    END,
    warehouse_tier,
    query_num,
    ctas_variant
