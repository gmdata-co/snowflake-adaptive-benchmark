-- CTAS Benchmark Query - Filtered Variant
-- Tests selective write with date filter
-- Produces ~2B rows × 16 columns at SF1000 (roughly 1/3 of LINEITEM based on date range)
-- Catalog: select_pathfinder
-- Schema: benchmark
SELECT *
FROM select_pathfinder.benchmark.lineitem
WHERE l_shipdate >= '1995-01-01';
