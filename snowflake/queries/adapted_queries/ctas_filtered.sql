-- CTAS Benchmark Query - Filtered Variant
-- Tests selective write with date filter
-- Produces ~2B rows × 16 columns at SF1000 (roughly 1/3 of LINEITEM based on date range)
SELECT *
FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.LINEITEM
WHERE l_shipdate >= '1995-01-01';
