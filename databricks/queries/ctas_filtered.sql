-- CTAS Benchmark Query - Filtered Variant
-- Tests selective write with date filter
-- Produces ~2B rows × 16 columns at SF1000 (roughly 1/3 of LINEITEM based on date range)
-- Catalog: ${DATABRICKS_CATALOG}
-- Schema: benchmark
SELECT *
FROM ${DATABRICKS_CATALOG}.benchmark.lineitem
WHERE l_shipdate >= '1995-01-01';
