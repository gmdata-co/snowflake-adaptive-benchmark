-- $ID$
-- TPC-H/TPC-R Product Type Profit Measure Query (Q9)
-- Functional Query Definition
-- Approved February 1998
select
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION,
	o_year,
	sum(amount) as sum_profit
from
	(
		select
			n_name as SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION,
			extract(year from o_orderdate) as o_year,
			l_extendedprice * (1 - l_discount) - ps_supplycost * l_quantity as amount
		from
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PART,
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.SUPPLIER,
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.LINEITEM,
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PARTSUPP,
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.ORDERS,
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION
		where
			s_suppkey = l_suppkey
			and ps_suppkey = l_suppkey
			and ps_partkey = l_partkey
			and p_partkey = l_partkey
			and o_orderkey = l_orderkey
			and s_nationkey = n_nationkey
			and p_name like '%green%'
	) as profit
group by
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION,
	o_year
order by
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION,
	o_year desc;
