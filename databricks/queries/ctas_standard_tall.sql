-- CTAS Benchmark Query - Standard Tall Variant
-- Tests full table copy with all columns
-- Produces ~6B rows × 16 columns at SF1000
-- Catalog: select_pathfinder
-- Schema: benchmark
SELECT *
FROM select_pathfinder.benchmark.lineitem;
