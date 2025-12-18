-- CTAS Benchmark Query - Medium Wide Variant
-- Tests moderate join with customer dimensions
-- Produces ~1.5B rows × ~30 columns at SF1000
SELECT
    -- Orders columns
    o.o_orderkey,
    o.o_custkey,
    o.o_orderstatus,
    o.o_totalprice,
    o.o_orderdate,
    o.o_orderpriority,
    o.o_clerk,
    o.o_shippriority,
    o.o_comment,
    -- Customer columns
    c.c_custkey AS c_custkey_dup,
    c.c_name,
    c.c_address,
    c.c_nationkey,
    c.c_phone,
    c.c_acctbal,
    c.c_mktsegment,
    c.c_comment,
    -- Nation columns
    n.n_nationkey,
    n.n_name,
    n.n_regionkey,
    n.n_comment,
    -- Region columns
    r.r_regionkey AS r_regionkey_dup,
    r.r_name,
    r.r_comment
FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.ORDERS o
JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.CUSTOMER c ON o.o_custkey = c.c_custkey
JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION n ON c.c_nationkey = n.n_nationkey
JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.REGION r ON n.n_regionkey = r.r_regionkey;
