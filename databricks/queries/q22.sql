-- $ID$
-- TPC-H/TPC-R Global Sales Opportunity Query (Q22)
-- Functional Query Definition
-- Approved February 1998
-- Adapted for Databricks from Snowflake TPC-H query
-- Catalog: ${DATABRICKS_CATALOG}
-- Schema: benchmark
-- Scale Factor: SF1000 (1TB)
--

select
	cntrycode,
	count(*) as numcust,
	sum(c_acctbal) as totacctbal
from
	(
		select
			SUBSTR(c_phone, 1, 2) as cntrycode,
			c_acctbal
		from ${DATABRICKS_CATALOG}.benchmark.customer
		where
			SUBSTR(c_phone, 1, 2) in
				('13', '31', '23', '29', '30', '18', '17')
			and c_acctbal > (
				select
					avg(c_acctbal)
				from ${DATABRICKS_CATALOG}.benchmark.customer
				where
					c_acctbal > 0.00
					and SUBSTR(c_phone, 1, 2) in
						('13', '31', '23', '29', '30', '18', '17')
			)
			and not exists (
				select
					*
				from ${DATABRICKS_CATALOG}.benchmark.orders
				where
					o_custkey = c_custkey
			)
	) as custsale
group by
	cntrycode
order by
	cntrycode;
