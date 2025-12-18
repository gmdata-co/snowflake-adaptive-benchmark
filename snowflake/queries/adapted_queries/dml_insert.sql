-- DML Insert: Re-insert the monthly slice of lineitem data from source
-- Target: June 1995 (~7.48M rows, ~1.25% of data)
INSERT INTO BENCHMARK.BENCHMARK.LINEITEM_DML
SELECT *
FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.LINEITEM
WHERE l_shipdate >= '1995-06-01'
  AND l_shipdate < '1995-07-01';
