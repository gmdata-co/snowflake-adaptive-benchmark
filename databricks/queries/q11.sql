-- $ID$
-- TPC-H/TPC-R Important Stock Identification Query (Q11)
-- Functional Query Definition
-- Approved February 1998
-- Adapted for Databricks from Snowflake TPC-H query
-- Catalog: select_pathfinder
-- Schema: benchmark
-- Scale Factor: SF1000 (1TB)
--

select
	ps_partkey,
	sum(ps_supplycost * ps_availqty) as value
from select_pathfinder.benchmark.partSUPP,
	select_pathfinder.benchmark.supplier,
	select_pathfinder.benchmark.nation
where
	ps_suppkey = s_suppkey
	and s_nationkey = n_nationkey
	and n_name = 'GERMANY'
group by
	ps_partkey having
		sum(ps_supplycost * ps_availqty) > (
			select
				sum(ps_supplycost * ps_availqty) * 0.0001
			from select_pathfinder.benchmark.partSUPP,
				select_pathfinder.benchmark.supplier,
				select_pathfinder.benchmark.nation
			where
				ps_suppkey = s_suppkey
				and s_nationkey = n_nationkey
				and n_name = 'GERMANY'
		)
order by
	value desc;
