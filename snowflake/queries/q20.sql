-- $ID$
-- TPC-H/TPC-R Potential SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PART Promotion Query (Q20)
-- Function Query Definition
-- Approved February 1998
select
	s_name,
	s_address
from
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.SUPPLIER,
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION
where
	s_suppkey in (
		select
			ps_suppkey
		from
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PARTSUPP
		where
			ps_partkey in (
				select
					p_partkey
				from
					SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PART
				where
					p_name like 'forest%'
			)
			and ps_availqty > (
				select
					0.5 * sum(l_quantity)
				from
					SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.LINEITEM
				where
					l_partkey = ps_partkey
					and l_suppkey = ps_suppkey
					and l_shipdate >= date '1994-01-01'
					and l_shipdate < date '1994-01-01' + interval '1' year
			)
	)
	and s_nationkey = n_nationkey
	and n_name = 'CANADA'
order by
	s_name;
