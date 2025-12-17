-- CTAS Benchmark Query - Medium Wide Variant
-- Tests moderate join with customer dimensions
-- Produces ~1.5B rows × ~30 columns at SF1000
-- Catalog: select_pathfinder
-- Schema: benchmark
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
FROM select_pathfinder.benchmark.orders o
JOIN select_pathfinder.benchmark.customer c ON o.o_custkey = c.c_custkey
JOIN select_pathfinder.benchmark.nation n ON c.c_nationkey = n.n_nationkey
JOIN select_pathfinder.benchmark.region r ON n.n_regionkey = r.r_regionkey;
