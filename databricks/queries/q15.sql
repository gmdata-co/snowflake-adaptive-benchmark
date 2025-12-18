WITH revenue0 (supplier_no, total_revenue) AS (
-- Adapted for Databricks from Snowflake TPC-H query
-- Catalog: ${DATABRICKS_CATALOG}
-- Schema: benchmark
-- Scale Factor: SF1000 (1TB)
--

select
		l_suppkey,
		sum(l_extendedprice * (1 - l_discount))
	from ${DATABRICKS_CATALOG}.benchmark.lineitem
	where
		l_shipdate >= date '1996-01-01'
		and l_shipdate < date '1996-01-01' + INTERVAL 3 month
	group by
		l_suppkey
)
select
	s_suppkey,
	s_name,
	s_address,
	s_phone,
	total_revenue
from ${DATABRICKS_CATALOG}.benchmark.supplier,
	revenue0
where
	s_suppkey = supplier_no
	and total_revenue = (
		select
			max(total_revenue)
		from
			revenue0
	)
order by
	s_suppkey
