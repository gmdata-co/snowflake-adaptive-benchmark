# TPC-H SF1000 Data Generation for Databricks

This guide explains how to generate TPC-H SF1000 (1TB) dataset in Databricks to match your Snowflake setup.

## Quick Summary

- **Target**: `select_pathfinder.benchmark` schema
- **Scale**: SF1000 (~1TB of data)
- **Approach**: Natural load order, NO clustering/partitioning
- **Estimated Time**: 3-6 hours
- **Estimated Cost**: $600-1200

## Fair Comparison Requirements

✅ **DO**:
- Generate data using standard tpch-dbgen tool
- Load in natural generation order
- Store as Delta Lake format
- Let Delta handle automatic compression only

❌ **DO NOT**:
- Apply Z-ordering or clustering
- Use date partitioning
- Run OPTIMIZE or VACUUM before benchmarking
- Add custom indexes or statistics

## Recommended Approach: Use Databricks Samples + Scaling

The easiest way is to use Databricks' built-in TPC-H sample and scale it up:

### Step 1: Check Available Samples

```sql
-- In Databricks SQL Editor
SHOW TABLES IN samples.tpch;
```

Databricks provides TPC-H data at SF1, SF10, SF100, and sometimes SF1000 scales.

### Step 2: Copy to Your Schema

If SF1000 exists in samples:

```sql
USE CATALOG select_pathfinder;
USE SCHEMA benchmark;

-- Copy each table (example for REGION - smallest table)
CREATE TABLE region AS
SELECT * FROM samples.tpch.region;

-- Repeat for all 8 tables:
-- nation, supplier, customer, part, partsupp, orders, lineitem
```

### Step 3: If SF1000 Not Available - Use tpch-dbgen

If Databricks doesn't have SF1000 in samples, you'll need to generate it.

**Option A: Databricks Notebook (Recommended)**

1. Create a new notebook in Databricks
2. Attach to your `benchmark_wh_small` SQL Warehouse
3. Use this code:

```python
# Install tpch-kit
%pip install git+https://github.com/databricks/tpch-kit.git

# Generate data
from tpch import  *

# Configure
scale_factor = 1000
location = "s3://YOUR-BUCKET/tpch-sf1000"  # Update with your storage
catalog = "select_pathfinder"
schema = "benchmark"

# Generate (this will take several hours)
generate_data(
    scale_factor=scale_factor,
    location=location,
    num_partitions=1000  # Parallelism
)

# Create Delta tables
create_tables(
    catalog=catalog,
    schema=schema,
    location=location,
    format="delta",
    partitioned=False  # NO partitioning for fair comparison
)
```

**Option B: Use spark-sql-perf**

```scala
// In a Scala notebook
import com.databricks.spark.sql.perf.tpch.TPCHTables

val scaleFactor = "1000"
val tables = new TPCHTables(spark.sqlContext,
    dsdgenDir = "/tmp/tpch-dbgen",
    scaleFactor = scaleFactor)

// Generate data
tables.genData(
    location = "s3://YOUR-BUCKET/tpch-sf1000",
    format = "parquet",
    overwrite = true,
    partitionTables = false,  // NO partitioning
    clusterByPartitionColumns = false,  // NO clustering
    numPartitions = 1000)

// Create Delta tables
tables.createExternalTables(
    "select_pathfinder.benchmark",
    "delta",
    overwrite = true)
```

## Validation

After generation, validate the data:

### Check Row Counts

```sql
-- Expected row counts for SF1000
SELECT 'region' as table_name, COUNT(*) as row_count, 5 as expected FROM region
UNION ALL
SELECT 'nation', COUNT(*), 25 FROM nation
UNION ALL
SELECT 'supplier', COUNT(*), 10000000 FROM supplier
UNION ALL
SELECT 'customer', COUNT(*), 150000000 FROM customer
UNION ALL
SELECT 'part', COUNT(*), 200000000 FROM part
UNION ALL
SELECT 'partsupp', COUNT(*), 800000000 FROM partsupp
UNION ALL
SELECT 'orders', COUNT(*), 1500000000 FROM orders
UNION ALL
SELECT 'lineitem', COUNT(*), 6000000000 FROM lineitem;
```

### Check Table Properties

```sql
-- Verify NO clustering (should show no cluster keys)
DESCRIBE DETAIL lineitem;

-- Check Delta properties
SHOW TBLPROPERTIES lineitem;
```

### Run Sample Queries

```sql
-- Test query on largest table
SELECT
    l_returnflag,
    l_linestatus,
    COUNT(*) as count_order
FROM lineitem
WHERE l_shipdate <= DATE '1998-09-02'
GROUP BY l_returnflag, l_linestatus
ORDER BY l_returnflag, l_linestatus;
```

## Alternative: Export from Snowflake

If generation proves too complex or expensive, you can export from Snowflake:

```sql
-- In Snowflake
COPY INTO @my_s3_stage/tpch-sf1000/lineitem/
FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000.LINEITEM
FILE_FORMAT = (TYPE = PARQUET)
HEADER = TRUE;

-- Repeat for all tables
```

Then in Databricks:

```sql
CREATE TABLE lineitem
USING DELTA
LOCATION 's3://your-bucket/tpch-sf1000/lineitem'
AS SELECT * FROM parquet.`s3://your-bucket/tpch-sf1000/lineitem/*.parquet`;
```

## Next Steps

After data generation:

1. Run validation queries
2. Update `databricks/config.py` if needed
3. Create adapted TPC-H queries for Databricks
4. Run benchmark with `databricks/benchmark.py`

## Troubleshooting

**Generation takes too long**:
- Use larger warehouse (Medium or Large)
- Increase num_partitions for more parallelism
- Consider using smaller scale (SF100) for initial testing

**Out of memory errors**:
- Increase cluster size
- Process tables individually (start with smaller tables)
- Use Databricks SQL Warehouse instead of clusters

**Cost concerns**:
- Start with SF100 to test the process (cost: ~$100)
- Use spot instances for generation
- Auto-stop warehouses when not in use

## Resources

- [Databricks TPC-H dbgen](https://github.com/databricks/tpch-dbgen)
- [spark-sql-perf](https://github.com/databricks/spark-sql-perf)
- [TPC-H Specification](http://www.tpc.org/tpch/)
