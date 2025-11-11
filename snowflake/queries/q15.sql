-- $ID$
-- TPC-H/TPC-R Top SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.SUPPLIER Query (Q15)
-- Functional Query Definition
-- Approved February 1998
create view revenue:s (supplier_no, total_revenue) as
	select
		l_suppkey,
		sum(l_extendedprice * (1 - l_discount))
	from
		SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.LINEITEM
	where
		l_shipdate >= date '1996-01-01'
		and l_shipdate < date '1996-01-01' + interval '3' month
	group by
		l_suppkey;

select
	s_suppkey,
	s_name,
	s_address,
	s_phone,
	total_revenue
from
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.SUPPLIER,
	revenue:s
where
	s_suppkey = supplier_no
	and total_revenue = (
		select
			max(total_revenue)
		from
			revenue:s
	)
order by
	s_suppkey;

drop view revenue:s;
