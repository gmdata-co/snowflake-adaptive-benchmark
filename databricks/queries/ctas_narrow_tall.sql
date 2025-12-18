-- CTAS Benchmark Query - Narrow Tall Variant
-- Tests pure write throughput with minimal column width
-- Produces ~6B rows × 4 columns at SF1000
-- Catalog: select_pathfinder
-- Schema: benchmark
SELECT
    l_orderkey,
    l_partkey,
    l_quantity,
    l_extendedprice
FROM select_pathfinder.benchmark.lineitem;
