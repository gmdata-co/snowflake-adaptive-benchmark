-- CTAS Benchmark Query - Standard Tall Variant
-- Tests full table copy with all columns
-- Produces ~6B rows × 16 columns at SF1000
-- Catalog: ${DATABRICKS_CATALOG}
-- Schema: benchmark
SELECT *
FROM ${DATABRICKS_CATALOG}.benchmark.lineitem;
