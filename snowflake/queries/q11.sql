-- $ID$
-- TPC-H/TPC-R Important Stock Identification Query (Q11)
-- Functional Query Definition
-- Approved February 1998
select
	ps_partkey,
	sum(ps_supplycost * ps_availqty) as value
from
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PARTSUPP,
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.SUPPLIER,
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION
where
	ps_suppkey = s_suppkey
	and s_nationkey = n_nationkey
	and n_name = 'GERMANY'
group by
	ps_partkey having
		sum(ps_supplycost * ps_availqty) > (
			select
				sum(ps_supplycost * ps_availqty) * 0.0001
			from
				SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PARTSUPP,
				SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.SUPPLIER,
				SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION
			where
				ps_suppkey = s_suppkey
				and s_nationkey = n_nationkey
				and n_name = 'GERMANY'
		)
order by
	value desc;
