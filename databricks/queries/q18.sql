-- $ID$
-- TPC-H/TPC-R Large Volume Customer Query (Q18)
-- Function Query Definition
-- Approved February 1998
-- Adapted for Databricks from Snowflake TPC-H query
-- Catalog: ${DATABRICKS_CATALOG}
-- Schema: benchmark
-- Scale Factor: SF1000 (1TB)
--

select
	c_name,
	c_custkey,
	o_orderkey,
	o_orderdate,
	o_totalprice,
	sum(l_quantity)
from ${DATABRICKS_CATALOG}.benchmark.customer,
	${DATABRICKS_CATALOG}.benchmark.orders,
	${DATABRICKS_CATALOG}.benchmark.lineitem
where
	o_orderkey in (
		select
			l_orderkey
		from ${DATABRICKS_CATALOG}.benchmark.lineitem
		group by
			l_orderkey having
				sum(l_quantity) > 300
	)
	and c_custkey = o_custkey
	and o_orderkey = l_orderkey
group by
	c_name,
	c_custkey,
	o_orderkey,
	o_orderdate,
	o_totalprice
order by
	o_totalprice desc,
	o_orderdate;
