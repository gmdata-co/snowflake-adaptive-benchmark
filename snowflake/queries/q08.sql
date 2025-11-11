-- $ID$
-- TPC-H/TPC-R National Market Share Query (Q8)
-- Functional Query Definition
-- Approved February 1998
select
	o_year,
	sum(case
		when SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION = 'BRAZIL' then volume
		else 0
	end) / sum(volume) as mkt_share
from
	(
		select
			extract(year from o_orderdate) as o_year,
			l_extendedprice * (1 - l_discount) as volume,
			n2.n_name as SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION
		from
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PART,
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.SUPPLIER,
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.LINEITEM,
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.ORDERS,
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.CUSTOMER,
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION n1,
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION n2,
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.REGION
		where
			p_partkey = l_partkey
			and s_suppkey = l_suppkey
			and l_orderkey = o_orderkey
			and o_custkey = c_custkey
			and c_nationkey = n1.n_nationkey
			and n1.n_regionkey = r_regionkey
			and r_name = 'AMERICA'
			and s_nationkey = n2.n_nationkey
			and o_orderdate between date '1995-01-01' and date '1996-12-31'
			and p_type = 'ECONOMY ANODIZED STEEL'
	) as all_nations
group by
	o_year
order by
	o_year;
