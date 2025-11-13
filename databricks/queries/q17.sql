-- $ID$
-- TPC-H/TPC-R Small-Quantity-Order Revenue Query (Q17)
-- Functional Query Definition
-- Approved February 1998
-- Adapted for Databricks from Snowflake TPC-H query
-- Catalog: select_pathfinder
-- Schema: benchmark
-- Scale Factor: SF1000 (1TB)
--

select
	sum(l_extendedprice) / 7.0 as avg_yearly
from select_pathfinder.benchmark.lineitem,
	select_pathfinder.benchmark.part
where
	p_partkey = l_partkey
	and p_brand = 'Brand#23'
	and p_container = 'MED BOX'
	and l_quantity < (
		select
			0.2 * avg(l_quantity)
		from select_pathfinder.benchmark.lineitem
		where
			l_partkey = p_partkey
	);
