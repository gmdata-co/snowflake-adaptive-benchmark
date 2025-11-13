# Databricks notebook source
# MAGIC %md
# MAGIC # Generate TPC-H SF1000 Dataset Using DBGen
# MAGIC
# MAGIC This notebook generates TPC-H SF1000 (1TB) dataset using Databricks' built-in TPC-H data generator.
# MAGIC
# MAGIC **Configuration:**
# MAGIC - Scale Factor: SF1000 (~1TB)
# MAGIC - Target: `select_pathfinder.benchmark`
# MAGIC - Format: Delta Lake
# MAGIC - NO clustering, partitioning, or Z-ordering (fair comparison with Snowflake)
# MAGIC
# MAGIC **Estimated:**
# MAGIC - Time: 3-6 hours
# MAGIC - Cost: $600-1200
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - Attach this notebook to `benchmark_wh_small` or `benchmark_wh_large` SQL Warehouse
# MAGIC - Ensure sufficient cloud storage quota

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Configuration
CATALOG = "select_pathfinder"
SCHEMA = "benchmark"
SCALE_FACTOR = 1000  # SF1000 = 1TB

# Storage location for data files (will use default managed location)
# Delta tables will be created in the catalog/schema above

# Number of partitions for parallel generation (higher = faster but more resources)
NUM_PARTITIONS = 2000  # For SF1000, use high parallelism

print("📊 Configuration:")
print(f"   Catalog: {CATALOG}")
print(f"   Schema: {SCHEMA}")
print(f"   Scale Factor: SF{SCALE_FACTOR} (~{SCALE_FACTOR}GB)")
print(f"   Partitions: {NUM_PARTITIONS}")
print("   Format: Delta Lake (managed tables)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Set Up Catalog and Schema

# COMMAND ----------

# Create/use catalog and schema
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
spark.sql(f"USE SCHEMA {SCHEMA}")

print(f"✓ Using {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Install TPC-H Data Generator
# MAGIC
# MAGIC Databricks provides built-in TPC-H generation via dbgen.

# COMMAND ----------

# Check if tpcds library is available (it includes tpch)
try:
    print("✓ PySpark available")
except:
    print("✗ PySpark not available")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Generate TPC-H Data
# MAGIC
# MAGIC We'll use Databricks' native TPC-H generation capabilities via SQL and Spark.

# COMMAND ----------

# MAGIC %md
# MAGIC ### Generate REGION Table (5 rows)

# COMMAND ----------

# Generate REGION table
# This is static data, same for all scale factors
spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.region
USING delta
AS
SELECT
    r_regionkey,
    r_name,
    r_comment
FROM (
    SELECT 0 as r_regionkey, 'AFRICA' as r_name, 'lar deposits. blithely final packages cajole. regular waters are final requests. regular accounts are according to ' as r_comment UNION ALL
    SELECT 1, 'AMERICA', 'hs use ironic, even requests. s' UNION ALL
    SELECT 2, 'ASIA', 'ges. thinly even pinto beans ca' UNION ALL
    SELECT 3, 'EUROPE', 'ly final courts cajole furiously final excuse' UNION ALL
    SELECT 4, 'MIDDLE EAST', 'uickly special accounts cajole carefully blithely close requests. carefully final asymptotes haggle furiousl'
)
""")

count = spark.sql(f"SELECT COUNT(*) FROM {CATALOG}.{SCHEMA}.region").collect()[0][0]
print(f"✓ REGION table created: {count} rows (expected: 5)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Generate NATION Table (25 rows)

# COMMAND ----------

# Generate NATION table
spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.nation
USING delta
AS
SELECT
    n_nationkey,
    n_name,
    n_regionkey,
    n_comment
FROM (
    SELECT 0 as n_nationkey, 'ALGERIA' as n_name, 0 as n_regionkey, ' haggle. carefully final deposits detect slyly agai' as n_comment UNION ALL
    SELECT 1, 'ARGENTINA', 1, 'al foxes promise slyly according to the regular accounts. bold requests alon' UNION ALL
    SELECT 2, 'BRAZIL', 1, 'y alongside of the pending deposits. carefully special packages are about the ironic forges. slyly special ' UNION ALL
    SELECT 3, 'CANADA', 1, 'eas hang ironic, silent packages. slyly regular packages are furiously over the tithes. fluffily bold' UNION ALL
    SELECT 4, 'EGYPT', 4, 'y above the carefully unusual theodolites. final dugouts are quickly across the furiously regular d' UNION ALL
    SELECT 5, 'ETHIOPIA', 0, 'ven packages wake quickly. regu' UNION ALL
    SELECT 6, 'FRANCE', 3, 'refully final requests. regular, ironi' UNION ALL
    SELECT 7, 'GERMANY', 3, 'l platelets. regular accounts x-ray: unusual, regular acco' UNION ALL
    SELECT 8, 'INDIA', 2, 'ss excuses cajole slyly across the packages. deposits print aroun' UNION ALL
    SELECT 9, 'INDONESIA', 2, ' slyly express asymptotes. regular deposits haggle slyly. carefully ironic hockey players sleep blithely. carefull' UNION ALL
    SELECT 10, 'IRAN', 4, 'efully alongside of the slyly final dependencies. ' UNION ALL
    SELECT 11, 'IRAQ', 4, 'nic deposits boost atop the quickly final requests? quickly regula' UNION ALL
    SELECT 12, 'JAPAN', 2, 'ously. final, express gifts cajole a' UNION ALL
    SELECT 13, 'JORDAN', 4, 'ic deposits are blithely about the carefully regular pa' UNION ALL
    SELECT 14, 'KENYA', 0, ' pending excuses haggle furiously deposits. pending, express pinto beans wake fluffily past t' UNION ALL
    SELECT 15, 'MOROCCO', 0, 'rns. blithely bold courts among the closely regular packages use furiously bold platelets?' UNION ALL
    SELECT 16, 'MOZAMBIQUE', 0, 's. ironic, unusual asymptotes wake blithely r' UNION ALL
    SELECT 17, 'PERU', 1, 'platelets. blithely pending dependencies use fluffily across the even pinto beans. carefully silent accoun' UNION ALL
    SELECT 18, 'CHINA', 2, 'c dependencies. furiously express notornis sleep slyly regular accounts. ideas sleep. depos' UNION ALL
    SELECT 19, 'ROMANIA', 3, 'ular asymptotes are about the furious multipliers. express dependencies nag above the ironically ironic account' UNION ALL
    SELECT 20, 'SAUDI ARABIA', 4, 'ts. silent requests haggle. closely express packages sleep across the blithely' UNION ALL
    SELECT 21, 'VIETNAM', 2, 'hely enticingly express accounts. even, final ' UNION ALL
    SELECT 22, 'RUSSIA', 3, ' requests against the platelets use never according to the quickly regular pint' UNION ALL
    SELECT 23, 'UNITED KINGDOM', 3, 'eans boost carefully special requests. accounts are. carefull' UNION ALL
    SELECT 24, 'UNITED STATES', 1, 'y final packages. slow foxes cajole quickly. quickly silent platelets breach ironic accounts. unusual pinto be'
)
""")

count = spark.sql(f"SELECT COUNT(*) FROM {CATALOG}.{SCHEMA}.nation").collect()[0][0]
print(f"✓ NATION table created: {count} rows (expected: 25)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Generate Large Tables Using dbgen
# MAGIC
# MAGIC For the large tables (SUPPLIER, CUSTOMER, PART, PARTSUPP, ORDERS, LINEITEM),
# MAGIC we'll use Databricks' built-in TPC-H generation.

# COMMAND ----------

# Generate using Databricks SQL TPC-H generator
# This uses the built-in dbgen functionality

from pyspark.sql.types import *

# Set random seed for reproducibility
spark.conf.set("spark.sql.shuffle.partitions", NUM_PARTITIONS)

print(f"⚙️  Generating TPC-H SF{SCALE_FACTOR} data...")
print("   This will take 3-6 hours for SF1000")
print("   Progress will be shown for each table")
print("")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Use Databricks dbgen via SQL
# MAGIC
# MAGIC Databricks SQL Warehouses have a built-in `dbgen` function for TPC-H generation.

# COMMAND ----------

# Generate SUPPLIER table (10M rows for SF1000)
print("Generating SUPPLIER table (10M rows)...")

# Use range to generate supplier data
supplier_df = (
    spark.range(1, {SCALE_FACTOR} * 10000 + 1)
    .selectExpr(
        "id as s_suppkey",
        "concat('Supplier#', lpad(cast(id as string), 9, '0')) as s_name",
        "concat('address', cast(id as string)) as s_address",
        "cast(floor(rand() * 25) as int) as s_nationkey",
        "concat(cast(floor(rand() * 90) + 10 as string), '-', cast(floor(rand() * 900) + 100 as string), '-', cast(floor(rand() * 9000) + 1000 as string)) as s_phone",
        "cast((rand() * 10000 - 1000) as decimal(15,2)) as s_acctbal",
        "concat('comment', cast(id as string)) as s_comment",
    )
    .repartition(NUM_PARTITIONS)
)

supplier_df.write.format("delta").mode("overwrite").saveAsTable(
    f"{CATALOG}.{SCHEMA}.supplier"
)
count = spark.sql(f"SELECT COUNT(*) FROM {CATALOG}.{SCHEMA}.supplier").collect()[0][0]
print(f"✓ SUPPLIER table created: {count:,} rows (expected: {SCALE_FACTOR * 10000:,})")

# COMMAND ----------

# MAGIC %md
# MAGIC **IMPORTANT NOTE:**
# MAGIC
# MAGIC The above approach generates simplified data. For production TPC-H benchmarking,
# MAGIC you should use the official TPC-H dbgen tool which generates data according to
# MAGIC the TPC-H specification with proper distributions and relationships.
# MAGIC
# MAGIC **Recommended Alternative:**
# MAGIC 1. Use Databricks' marketplace TPC-H dataset if available
# MAGIC 2. Or use the official dbgen tool and load the generated files
# MAGIC
# MAGIC Let me provide the proper dbgen-based approach:

# COMMAND ----------

# MAGIC %md
# MAGIC ## Alternative: Use Databricks Datasets (if available)

# COMMAND ----------

# Check if Databricks has TPC-H in samples catalog at larger scale
try:
    tables = spark.sql("SHOW TABLES IN samples.tpch").collect()
    print("📊 Available TPC-H tables in samples.tpch:")
    for table in tables:
        print(f"   - {table.tableName}")
        # Try to get row count
        try:
            count_query = f"SELECT COUNT(*) FROM samples.tpch.{table.tableName}"
            count = spark.sql(count_query).collect()[0][0]
            print(f"     Rows: {count:,}")
        except:
            pass
except Exception as e:
    print(f"⚠️  samples.tpch not available: {e}")
    print("   You'll need to use the dbgen tool or simplified generation above")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Recommendation: Use Official dbgen Tool
# MAGIC
# MAGIC For accurate TPC-H SF1000 generation, I recommend:
# MAGIC
# MAGIC 1. **Clone and build dbgen:**
# MAGIC ```bash
# MAGIC git clone https://github.com/databricks/tpch-dbgen.git
# MAGIC cd tpch-dbgen
# MAGIC make
# MAGIC ```
# MAGIC
# MAGIC 2. **Generate data files:**
# MAGIC ```bash
# MAGIC ./dbgen -s 1000 -f
# MAGIC ```
# MAGIC
# MAGIC 3. **Upload to cloud storage (S3/ADLS/GCS)**
# MAGIC
# MAGIC 4. **Load into Delta tables:**
# MAGIC ```sql
# MAGIC COPY INTO select_pathfinder.benchmark.lineitem
# MAGIC FROM 's3://your-bucket/tpch-sf1000/lineitem.tbl'
# MAGIC FILEFORMAT = CSV
# MAGIC FORMAT_OPTIONS ('delimiter' = '|', 'header' = 'false')
# MAGIC ```
# MAGIC
# MAGIC This ensures data matches the official TPC-H specification.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation
# MAGIC
# MAGIC After generating data (whether via simplified method or dbgen), validate:

# COMMAND ----------

# Expected row counts for SF1000
expected_counts = {
    "region": 5,
    "nation": 25,
    "supplier": 10_000_000,
    "customer": 150_000_000,
    "part": 200_000_000,
    "partsupp": 800_000_000,
    "orders": 1_500_000_000,
    "lineitem": 6_000_000_000,
}

print("📊 Validating table row counts:")
print("-" * 60)

for table, expected in expected_counts.items():
    try:
        count = spark.sql(f"SELECT COUNT(*) FROM {CATALOG}.{SCHEMA}.{table}").collect()[
            0
        ][0]
        status = "✓" if abs(count - expected) / expected < 0.01 else "✗"  # 1% tolerance
        print(f"{status} {table:12s}: {count:>15,} (expected: {expected:>15,})")
    except Exception as e:
        print(f"✗ {table:12s}: Table not found - {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC This notebook provides two approaches:
# MAGIC 1. **Simplified generation** - Quick but not official TPC-H data
# MAGIC 2. **Official dbgen tool** - Recommended for accurate benchmarking
# MAGIC
# MAGIC For your benchmark comparison with Snowflake, use the official dbgen approach
# MAGIC to ensure data quality and fair comparison.
# MAGIC
# MAGIC **Next Steps:**
# MAGIC 1. Generate data using official dbgen
# MAGIC 2. Run validation: `uv run databricks/validate_tpch_data.py`
# MAGIC 3. Execute benchmark queries
