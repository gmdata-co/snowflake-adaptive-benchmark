-- $ID$
-- TPC-H/TPC-R Shipping Priority Query (Q3)
-- Functional Query Definition
-- Approved February 1998
-- Adapted for Databricks from Snowflake TPC-H query
-- Catalog: select_pathfinder
-- Schema: benchmark
-- Scale Factor: SF1000 (1TB)
--

select
	l_orderkey,
	sum(l_extendedprice * (1 - l_discount)) as revenue,
	o_orderdate,
	o_shippriority
from select_pathfinder.benchmark.customer,
	select_pathfinder.benchmark.orders,
	select_pathfinder.benchmark.lineitem
where
	c_mktsegment = 'BUILDING'
	and c_custkey = o_custkey
	and l_orderkey = o_orderkey
	and o_orderdate < date '1995-03-15'
	and l_shipdate > date '1995-03-15'
group by
	l_orderkey,
	o_orderdate,
	o_shippriority
order by
	revenue desc,
	o_orderdate;
