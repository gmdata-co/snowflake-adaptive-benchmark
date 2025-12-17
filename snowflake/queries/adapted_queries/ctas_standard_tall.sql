-- CTAS Benchmark Query - Standard Tall Variant
-- Tests full table copy with all columns
-- Produces ~6B rows × 16 columns at SF1000
SELECT *
FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.LINEITEM;
