-- $ID$
-- TPC-H/TPC-R Small-Quantity-Order Revenue Query (Q17)
-- Functional Query Definition
-- Approved February 1998
-- Adapted for Databricks from Snowflake TPC-H query
-- Catalog: ${DATABRICKS_CATALOG}
-- Schema: benchmark
-- Scale Factor: SF1000 (1TB)
--

select
	sum(l_extendedprice) / 7.0 as avg_yearly
from ${DATABRICKS_CATALOG}.benchmark.lineitem,
	${DATABRICKS_CATALOG}.benchmark.part
where
	p_partkey = l_partkey
	and p_brand = 'Brand#23'
	and p_container = 'MED BOX'
	and l_quantity < (
		select
			0.2 * avg(l_quantity)
		from ${DATABRICKS_CATALOG}.benchmark.lineitem
		where
			l_partkey = p_partkey
	);
