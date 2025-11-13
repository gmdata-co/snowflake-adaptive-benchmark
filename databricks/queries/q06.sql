-- $ID$
-- TPC-H/TPC-R Forecasting Revenue Change Query (Q6)
-- Functional Query Definition
-- Approved February 1998
-- Adapted for Databricks from Snowflake TPC-H query
-- Catalog: select_pathfinder
-- Schema: benchmark
-- Scale Factor: SF1000 (1TB)
--

select
	sum(l_extendedprice * l_discount) as revenue
from select_pathfinder.benchmark.lineitem
where
	l_shipdate >= date '1994-01-01'
	and l_shipdate < date '1994-01-01' + INTERVAL 1 year
	and l_discount between 0.06 - 0.01 and 0.06 + 0.01
	and l_quantity < 24;
