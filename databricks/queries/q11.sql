-- $ID$
-- TPC-H/TPC-R Important Stock Identification Query (Q11)
-- Functional Query Definition
-- Approved February 1998
-- Adapted for Databricks from Snowflake TPC-H query
-- Catalog: ${DATABRICKS_CATALOG}
-- Schema: benchmark
-- Scale Factor: SF1000 (1TB)
--

select
	ps_partkey,
	sum(ps_supplycost * ps_availqty) as value
from ${DATABRICKS_CATALOG}.benchmark.partSUPP,
	${DATABRICKS_CATALOG}.benchmark.supplier,
	${DATABRICKS_CATALOG}.benchmark.nation
where
	ps_suppkey = s_suppkey
	and s_nationkey = n_nationkey
	and n_name = 'GERMANY'
group by
	ps_partkey having
		sum(ps_supplycost * ps_availqty) > (
			select
				sum(ps_supplycost * ps_availqty) * 0.0001
			from ${DATABRICKS_CATALOG}.benchmark.partSUPP,
				${DATABRICKS_CATALOG}.benchmark.supplier,
				${DATABRICKS_CATALOG}.benchmark.nation
			where
				ps_suppkey = s_suppkey
				and s_nationkey = n_nationkey
				and n_name = 'GERMANY'
		)
order by
	value desc;
