-- $ID$
-- TPC-H/TPC-R Potential Part Promotion Query (Q20)
-- Function Query Definition
-- Approved February 1998
-- Adapted for Databricks from Snowflake TPC-H query
-- Catalog: ${DATABRICKS_CATALOG}
-- Schema: benchmark
-- Scale Factor: SF1000 (1TB)
--

select
	s_name,
	s_address
from ${DATABRICKS_CATALOG}.benchmark.supplier,
	${DATABRICKS_CATALOG}.benchmark.nation
where
	s_suppkey in (
		select
			ps_suppkey
		from ${DATABRICKS_CATALOG}.benchmark.partSUPP
		where
			ps_partkey in (
				select
					p_partkey
				from ${DATABRICKS_CATALOG}.benchmark.part
				where
					p_name like 'forest%'
			)
			and ps_availqty > (
				select
					0.5 * sum(l_quantity)
				from ${DATABRICKS_CATALOG}.benchmark.lineitem
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
