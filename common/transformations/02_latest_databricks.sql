-- Latest Databricks benchmark run
-- Shows results from the most recent run_id, first run_num only
CREATE OR REPLACE VIEW latest_databricks AS
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
FROM main.databricks_results
WHERE run_id = (
    SELECT run_id
    FROM main.databricks_results
    ORDER BY timestamp DESC
    LIMIT 1
)
AND run_num = (
    SELECT MIN(run_num)
    FROM main.databricks_results
    WHERE run_id = (
        SELECT run_id
        FROM main.databricks_results
        ORDER BY timestamp DESC
        LIMIT 1
    )
)
ORDER BY query_num;
