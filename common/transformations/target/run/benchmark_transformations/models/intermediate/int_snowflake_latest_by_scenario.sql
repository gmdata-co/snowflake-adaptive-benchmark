
  
  create view "benchmark_results"."main"."int_snowflake_latest_by_scenario__dbt_tmp" as (
    

-- Get latest Snowflake run for each scenario (first run_num only)
WITH latest_runs AS (
    SELECT
        scenario,
        MAX(timestamp) AS latest_timestamp
    FROM "benchmark_results"."main"."base_snowflake_results"
    GROUP BY scenario
),

latest_run_ids AS (
    SELECT DISTINCT
        r.scenario,
        r.run_id
    FROM "benchmark_results"."main"."base_snowflake_results" r
    INNER JOIN latest_runs l
        ON r.scenario = l.scenario
        AND r.timestamp = l.latest_timestamp
)

SELECT
    r.*
FROM "benchmark_results"."main"."base_snowflake_results" r
INNER JOIN latest_run_ids l
    ON r.run_id = l.run_id
    AND r.scenario = l.scenario
WHERE r.run_num = (
    SELECT MIN(run_num)
    FROM "benchmark_results"."main"."base_snowflake_results" sub
    WHERE sub.run_id = r.run_id
    AND sub.scenario = r.scenario
)
ORDER BY r.scenario, r.query_num
  );
