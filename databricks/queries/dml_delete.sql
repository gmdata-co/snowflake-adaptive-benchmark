-- DML Delete: Delete a monthly slice of lineitem data
-- Target: June 1995 (~7.48M rows, ~1.25% of data)
DELETE FROM select_pathfinder.benchmark.lineitem_dml
WHERE l_shipdate >= '1995-06-01'
  AND l_shipdate < '1995-07-01';
