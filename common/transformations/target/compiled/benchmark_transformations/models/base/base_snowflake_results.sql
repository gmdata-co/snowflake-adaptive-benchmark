

-- Base Snowflake results - passthrough for documentation and testing
SELECT
    run_id,
    timestamp,
    platform,
    scenario,
    warehouse_name,
    warehouse_size,
    query_num,
    run_num,
    run_type,
    query_tag,
    query_id,
    execution_time_sec,
    rows_produced,
    error_message,
    compilation_time_ms,
    queued_time_ms,
    bytes_scanned,
    credits_used_compute,
    credits_used_cloud_services,
    total_elapsed_time_ms
FROM "benchmark_results"."main"."snowflake_results"