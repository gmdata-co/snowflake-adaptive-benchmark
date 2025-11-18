-- Latest Databricks benchmark run with run_id and warehouse_id
-- Shows results from the most recent run_id, first run_num only
-- Note: warehouse_name in databricks_results table contains the warehouse_id
CREATE OR REPLACE VIEW dbx_latest_run AS
SELECT
    run_id,
    warehouse_name AS warehouse_id,
    timestamp,
    platform,
    scenario,
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
