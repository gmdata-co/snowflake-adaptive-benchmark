WITH revenue0 (supplier_no, total_revenue) AS (
select
		l_suppkey,
		sum(l_extendedprice * (1 - l_discount))
	from SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.LINEITEM
	where
		l_shipdate >= date '1996-01-01'
		and l_shipdate < date '1996-01-01' + INTERVAL '3 month'
	group by
		l_suppkey
)
select
	s_suppkey,
	s_name,
	s_address,
	s_phone,
	total_revenue
from SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.SUPPLIER,
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
