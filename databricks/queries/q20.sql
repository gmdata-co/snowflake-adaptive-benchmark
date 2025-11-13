-- $ID$
-- TPC-H/TPC-R Potential Part Promotion Query (Q20)
-- Function Query Definition
-- Approved February 1998
-- Adapted for Databricks from Snowflake TPC-H query
-- Catalog: select_pathfinder
-- Schema: benchmark
-- Scale Factor: SF1000 (1TB)
--

select
	s_name,
	s_address
from select_pathfinder.benchmark.supplier,
	select_pathfinder.benchmark.nation
where
	s_suppkey in (
		select
			ps_suppkey
		from select_pathfinder.benchmark.partSUPP
		where
			ps_partkey in (
				select
					p_partkey
				from select_pathfinder.benchmark.part
				where
					p_name like 'forest%'
			)
			and ps_availqty > (
				select
					0.5 * sum(l_quantity)
				from select_pathfinder.benchmark.lineitem
				where
					l_partkey = ps_partkey
					and l_suppkey = ps_suppkey
					and l_shipdate >= date '1994-01-01'
					and l_shipdate < date '1994-01-01' + INTERVAL 1 year
			)
	)
	and s_nationkey = n_nationkey
	and n_name = 'CANADA'
order by
	s_name;
