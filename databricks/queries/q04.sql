-- $ID$
-- TPC-H/TPC-R Order Priority Checking Query (Q4)
-- Functional Query Definition
-- Approved February 1998
-- Adapted for Databricks from Snowflake TPC-H query
-- Catalog: select_pathfinder
-- Schema: benchmark
-- Scale Factor: SF1000 (1TB)
--

select
	o_orderpriority,
	count(*) as order_count
from select_pathfinder.benchmark.orders
where
	o_orderdate >= date '1993-07-01'
	and o_orderdate < date '1993-07-01' + INTERVAL 3 month
	and exists (
		select
			*
		from select_pathfinder.benchmark.lineitem
		where
			l_orderkey = o_orderkey
			and l_commitdate < l_receiptdate
	)
group by
	o_orderpriority
order by
	o_orderpriority;
