-- Example DuckDB queries for analyzing benchmark results
-- Use with: uv run python analyze_results.py --sql "YOUR_QUERY_HERE"

-- 1. Find queries where XLARGE is not much faster than MEDIUM (poor scaling)
SELECT
    query_num,
    ROUND(AVG(CASE WHEN warehouse_size='MEDIUM' THEN execution_time_sec END), 3) as medium_avg,
    ROUND(AVG(CASE WHEN warehouse_size='XLARGE' THEN execution_time_sec END), 3) as xlarge_avg,
    ROUND(AVG(CASE WHEN warehouse_size='MEDIUM' THEN execution_time_sec END) -
          AVG(CASE WHEN warehouse_size='XLARGE' THEN execution_time_sec END), 3) as time_saved,
    ROUND((AVG(CASE WHEN warehouse_size='MEDIUM' THEN execution_time_sec END) -
           AVG(CASE WHEN warehouse_size='XLARGE' THEN execution_time_sec END)) /
          AVG(CASE WHEN warehouse_size='MEDIUM' THEN execution_time_sec END) * 100, 1) as pct_faster
FROM benchmark_results
WHERE run_type='warm'
GROUP BY query_num
HAVING pct_faster < 20  -- Less than 20% improvement
ORDER BY pct_faster ASC;


-- 2. Queries with high variance (inconsistent performance)
SELECT
    query_num,
    warehouse_size,
    ROUND(AVG(execution_time_sec), 3) as avg_time,
    ROUND(STDDEV(execution_time_sec), 3) as stddev,
    ROUND(STDDEV(execution_time_sec) / AVG(execution_time_sec) * 100, 1) as coeff_variation_pct
FROM benchmark_results
WHERE run_type='warm'
GROUP BY query_num, warehouse_size
HAVING coeff_variation_pct > 15  -- High variability
ORDER BY coeff_variation_pct DESC;


-- 3. ROI Analysis: Which queries benefit most from larger warehouse?
SELECT
    query_num,
    ROUND(AVG(CASE WHEN warehouse_size='SMALL' THEN execution_time_sec END), 3) as small_avg,
    ROUND(AVG(CASE WHEN warehouse_size='XLARGE' THEN execution_time_sec END), 3) as xlarge_avg,
    ROUND(AVG(CASE WHEN warehouse_size='SMALL' THEN execution_time_sec END) /
          AVG(CASE WHEN warehouse_size='XLARGE' THEN execution_time_sec END), 2) as speedup_ratio
FROM benchmark_results
WHERE run_type='warm'
GROUP BY query_num
ORDER BY speedup_ratio DESC
LIMIT 10;


-- 4. Semi-warm vs warm comparison (compilation/cache benefit)
SELECT
    query_num,
    warehouse_size,
    ROUND(AVG(CASE WHEN run_type='semi-warm' THEN execution_time_sec END), 3) as semi_warm_avg,
    ROUND(AVG(CASE WHEN run_type='warm' THEN execution_time_sec END), 3) as warm_avg,
    ROUND(AVG(CASE WHEN run_type='semi-warm' THEN execution_time_sec END) -
          AVG(CASE WHEN run_type='warm' THEN execution_time_sec END), 3) as cache_benefit_sec
FROM benchmark_results
GROUP BY query_num, warehouse_size
HAVING semi_warm_avg IS NOT NULL AND warm_avg IS NOT NULL
ORDER BY cache_benefit_sec DESC
LIMIT 15;


-- 5. Performance stability: Min/Max spread analysis
SELECT
    query_num,
    warehouse_size,
    ROUND(MIN(execution_time_sec), 3) as min_time,
    ROUND(MAX(execution_time_sec), 3) as max_time,
    ROUND(MAX(execution_time_sec) - MIN(execution_time_sec), 3) as spread,
    ROUND((MAX(execution_time_sec) - MIN(execution_time_sec)) / MIN(execution_time_sec) * 100, 1) as spread_pct
FROM benchmark_results
WHERE run_type='warm'
GROUP BY query_num, warehouse_size
ORDER BY spread_pct DESC
LIMIT 15;


-- 6. Quick summary by warehouse (useful for cost analysis)
SELECT
    warehouse_size,
    COUNT(*) as total_runs,
    COUNT(DISTINCT query_num) as queries_run,
    ROUND(SUM(execution_time_sec), 2) as total_exec_time_sec,
    ROUND(AVG(execution_time_sec), 3) as avg_exec_time,
    ROUND(SUM(execution_time_sec) / 3600, 2) as total_hours
FROM benchmark_results
GROUP BY warehouse_size
ORDER BY warehouse_size;


-- 7. Identify queries that get slower on larger warehouses (anti-pattern)
SELECT
    query_num,
    ROUND(AVG(CASE WHEN warehouse_size='SMALL' THEN execution_time_sec END), 3) as small_avg,
    ROUND(AVG(CASE WHEN warehouse_size='MEDIUM' THEN execution_time_sec END), 3) as medium_avg,
    ROUND(AVG(CASE WHEN warehouse_size='XLARGE' THEN execution_time_sec END), 3) as xlarge_avg
FROM benchmark_results
WHERE run_type='warm'
GROUP BY query_num
HAVING xlarge_avg > medium_avg OR medium_avg > small_avg
ORDER BY xlarge_avg DESC;


-- 8. Run-to-run stability within warm runs
WITH warm_runs AS (
    SELECT
        query_num,
        warehouse_size,
        run_num,
        execution_time_sec
    FROM benchmark_results
    WHERE run_type='warm'
)
SELECT
    query_num,
    warehouse_size,
    COUNT(*) as num_warm_runs,
    ROUND(MIN(execution_time_sec), 3) as min_warm,
    ROUND(MAX(execution_time_sec), 3) as max_warm,
    ROUND(AVG(execution_time_sec), 3) as avg_warm,
    ROUND(STDDEV(execution_time_sec), 3) as stddev_warm
FROM warm_runs
GROUP BY query_num, warehouse_size
ORDER BY stddev_warm DESC NULLS LAST
LIMIT 15;


-- 9. Execution time distribution by query complexity
SELECT
    CASE
        WHEN AVG(execution_time_sec) < 2 THEN 'Very Fast (<2s)'
        WHEN AVG(execution_time_sec) < 5 THEN 'Fast (2-5s)'
        WHEN AVG(execution_time_sec) < 10 THEN 'Medium (5-10s)'
        ELSE 'Slow (>10s)'
    END as speed_category,
    COUNT(DISTINCT query_num) as num_queries,
    ROUND(AVG(execution_time_sec), 3) as avg_time,
    string_agg(CAST(query_num AS VARCHAR), ', ' ORDER BY query_num) as queries
FROM (
    SELECT query_num, AVG(execution_time_sec) as execution_time_sec
    FROM benchmark_results
    WHERE run_type='warm'
    GROUP BY query_num
) subq
GROUP BY speed_category
ORDER BY avg_time;


-- 10. Warehouse efficiency: Time per query comparison
SELECT
    warehouse_size,
    query_num,
    ROUND(AVG(execution_time_sec), 3) as avg_exec_time,
    ROUND(MIN(execution_time_sec), 3) as best_time,
    COUNT(*) as runs
FROM benchmark_results
WHERE run_type='warm'
GROUP BY warehouse_size, query_num
ORDER BY query_num, warehouse_size;
