-- DML Insert: Re-insert the monthly slice of lineitem data from source
-- Target: June 1995 (~7.48M rows, ~1.25% of data)
INSERT INTO select_pathfinder.benchmark.lineitem_dml
SELECT *
FROM select_pathfinder.benchmark.lineitem
WHERE l_shipdate >= '1995-06-01'
  AND l_shipdate < '1995-07-01';
