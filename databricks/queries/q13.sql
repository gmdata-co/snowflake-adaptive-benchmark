-- $ID$
-- TPC-H/TPC-R Customer Distribution Query (Q13)
-- Functional Query Definition
-- Approved February 1998
-- Adapted for Databricks from Snowflake TPC-H query
-- Catalog: select_pathfinder
-- Schema: benchmark
-- Scale Factor: SF1000 (1TB)
--

select
	c_count,
	count(*) as custdist
from
	(
		select
			c_custkey,
			count(o_orderkey)
		from select_pathfinder.benchmark.customer left outer join select_pathfinder.benchmark.orders on
				c_custkey = o_custkey
				and o_comment not like '%special%requests%'
		group by
			c_custkey
	) as c_orders (c_custkey, c_count)
group by
	c_count
order by
	custdist desc,
	c_count desc;
