-- $ID$
-- TPC-H/TPC-R Local Supplier Volume Query (Q5)
-- Functional Query Definition
-- Approved February 1998
-- Adapted for Databricks from Snowflake TPC-H query
-- Catalog: ${DATABRICKS_CATALOG}
-- Schema: benchmark
-- Scale Factor: SF1000 (1TB)
--

select
	n_name,
	sum(l_extendedprice * (1 - l_discount)) as revenue
from ${DATABRICKS_CATALOG}.benchmark.customer,
	${DATABRICKS_CATALOG}.benchmark.orders,
	${DATABRICKS_CATALOG}.benchmark.lineitem,
	${DATABRICKS_CATALOG}.benchmark.supplier,
	${DATABRICKS_CATALOG}.benchmark.nation,
	${DATABRICKS_CATALOG}.benchmark.region
where
	c_custkey = o_custkey
	and l_orderkey = o_orderkey
	and l_suppkey = s_suppkey
	and c_nationkey = s_nationkey
	and s_nationkey = n_nationkey
	and n_regionkey = r_regionkey
	and r_name = 'ASIA'
	and o_orderdate >= date '1994-01-01'
	and o_orderdate < date '1994-01-01' + INTERVAL 1 year
group by
	n_name
order by
	revenue desc;
