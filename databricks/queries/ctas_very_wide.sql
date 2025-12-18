-- CTAS Benchmark Query - Very Wide Variant
-- Joins all TPC-H tables into a denormalized fact table
-- Produces one row per LINEITEM with all dimension attributes (~6B rows × 59 columns at SF1000)
-- Catalog: ${DATABRICKS_CATALOG}
-- Schema: benchmark
SELECT
    -- Lineitem (fact table)
    l.l_orderkey,
    l.l_partkey,
    l.l_suppkey,
    l.l_linenumber,
    l.l_quantity,
    l.l_extendedprice,
    l.l_discount,
    l.l_tax,
    l.l_returnflag,
    l.l_linestatus,
    l.l_shipdate,
    l.l_commitdate,
    l.l_receiptdate,
    l.l_shipinstruct,
    l.l_shipmode,
    l.l_comment AS l_comment,
    -- Orders
    o.o_orderstatus,
    o.o_totalprice,
    o.o_orderdate,
    o.o_orderpriority,
    o.o_clerk,
    o.o_shippriority,
    o.o_comment AS o_comment,
    -- Customer
    c.c_name,
    c.c_address AS c_address,
    c.c_phone AS c_phone,
    c.c_acctbal AS c_acctbal,
    c.c_mktsegment,
    c.c_comment AS c_comment,
    -- Part
    p.p_name,
    p.p_mfgr,
    p.p_brand,
    p.p_type,
    p.p_size,
    p.p_container,
    p.p_retailprice,
    p.p_comment AS p_comment,
    -- Supplier
    s.s_name,
    s.s_address AS s_address,
    s.s_phone AS s_phone,
    s.s_acctbal AS s_acctbal,
    s.s_comment AS s_comment,
    -- PartSupp
    ps.ps_availqty,
    ps.ps_supplycost,
    ps.ps_comment AS ps_comment,
    -- Customer Nation
    cn.n_name AS customer_nation,
    -- Supplier Nation
    sn.n_name AS supplier_nation,
    -- Customer Region
    cr.r_name AS customer_region,
    -- Supplier Region
    sr.r_name AS supplier_region
FROM ${DATABRICKS_CATALOG}.benchmark.lineitem l
JOIN ${DATABRICKS_CATALOG}.benchmark.orders o ON l.l_orderkey = o.o_orderkey
JOIN ${DATABRICKS_CATALOG}.benchmark.customer c ON o.o_custkey = c.c_custkey
JOIN ${DATABRICKS_CATALOG}.benchmark.part p ON l.l_partkey = p.p_partkey
JOIN ${DATABRICKS_CATALOG}.benchmark.supplier s ON l.l_suppkey = s.s_suppkey
JOIN ${DATABRICKS_CATALOG}.benchmark.partsupp ps ON l.l_partkey = ps.ps_partkey AND l.l_suppkey = ps.ps_suppkey
JOIN ${DATABRICKS_CATALOG}.benchmark.nation cn ON c.c_nationkey = cn.n_nationkey
JOIN ${DATABRICKS_CATALOG}.benchmark.nation sn ON s.s_nationkey = sn.n_nationkey
JOIN ${DATABRICKS_CATALOG}.benchmark.region cr ON cn.n_regionkey = cr.r_regionkey
JOIN ${DATABRICKS_CATALOG}.benchmark.region sr ON sn.n_regionkey = sr.r_regionkey;
