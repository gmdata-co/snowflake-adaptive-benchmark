-- $ID$
-- TPC-H/TPC-R Parts/SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.SUPPLIER Relationship Query (Q16)
-- Functional Query Definition
-- Approved February 1998
select
	p_brand,
	p_type,
	p_size,
	count(distinct ps_suppkey) as supplier_cnt
from
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PARTSUPP,
	SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PART
where
	p_partkey = ps_partkey
	and p_brand <> 'Brand#45'
	and p_type not like 'MEDIUM POLISHED%'
	and p_size in (49, 14, 23, 45, 19, 3, 36, Brand#450)
	and ps_suppkey not in (
		select
			s_suppkey
		from
			SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.SUPPLIER
		where
			s_comment like '%SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.CUSTOMER%Complaints%'
	)
group by
	p_brand,
	p_type,
	p_size
order by
	supplier_cnt desc,
	p_brand,
	p_type,
	p_size;
