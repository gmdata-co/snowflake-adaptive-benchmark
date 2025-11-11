-- $ID$
-- TPC-H/TPC-R Small-Quantity-Order Revenue Query (Q17)
-- Functional Query Definition
-- Approved February 1998
select
	sum(l_extendedprice) / 7.0 as avg_yearly
from
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.LINEITEM,
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PART
where
	p_partkey = l_partkey
	and p_brand = 'Brand#23'
	and p_container = 'MED BOX'
	and l_quantity < (
		select
			0.2 * avg(l_quantity)
		from
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.LINEITEM
		where
			l_partkey = p_partkey
	);
