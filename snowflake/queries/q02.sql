-- $ID$
-- TPC-H/TPC-R Minimum Cost SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.SUPPLIER Query (Q2)
-- Functional Query Definition
-- Approved February 1998
select
	s_acctbal,
	s_name,
	n_name,
	p_partkey,
	p_mfgr,
	s_address,
	s_phone,
	s_comment
from
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PART,
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.SUPPLIER,
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PARTSUPP,
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION,
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.REGION
where
	p_partkey = ps_partkey
	and s_suppkey = ps_suppkey
	and p_size = 15
	and p_type like '%BRASS'
	and s_nationkey = n_nationkey
	and n_regionkey = r_regionkey
	and r_name = 'EUROPE'
	and ps_supplycost = (
		select
			min(ps_supplycost)
		from
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PARTSUPP,
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.SUPPLIER,
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION,
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.REGION
		where
			p_partkey = ps_partkey
			and s_suppkey = ps_suppkey
			and s_nationkey = n_nationkey
			and n_regionkey = r_regionkey
			and r_name = 'EUROPE'
	)
order by
	s_acctbal desc,
	n_name,
	s_name,
	p_partkey;
