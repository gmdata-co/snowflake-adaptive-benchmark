# Databricks notebook source
# MAGIC %md
# MAGIC # Generate TPC-H Data for Benchmarking
# MAGIC
# MAGIC This notebook checks for existing TPC-H sample data and clones it for benchmarking.

# COMMAND ----------

# Configuration
CATALOG = "select_pathfinder"
SCHEMA = "benchmark"

print(f"Target: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# Create/use catalog and schema
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
spark.sql(f"USE SCHEMA {SCHEMA}")

print(f"✓ Using {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Static Tables

# COMMAND ----------

# Generate REGION table
spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.region
AS SELECT * FROM (
    SELECT 0 as r_regionkey, 'AFRICA' as r_name, 'lar deposits. blithely final packages cajole. regular waters are final requests. regular accounts are according to ' as r_comment UNION ALL
    SELECT 1, 'AMERICA', 'hs use ironic, even requests. s' UNION ALL
    SELECT 2, 'ASIA', 'ges. thinly even pinto beans ca' UNION ALL
    SELECT 3, 'EUROPE', 'ly final courts cajole furiously final excuse' UNION ALL
    SELECT 4, 'MIDDLE EAST', 'uickly special accounts cajole carefully blithely close requests. carefully final asymptotes haggle furiousl'
)
""")

print(f"✓ REGION: {spark.table(f'{CATALOG}.{SCHEMA}.region').count()} rows")

# COMMAND ----------

# Generate NATION table
spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.nation
AS SELECT * FROM (
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

print(f"✓ NATION: {spark.table(f'{CATALOG}.{SCHEMA}.nation').count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check for Sample TPC-H Data

# COMMAND ----------

# Check samples.tpch
try:
    tables = spark.sql("SHOW TABLES IN samples.tpch").collect()
    print(f"✓ Found {len(tables)} tables in samples.tpch:")
    for t in tables:
        count = spark.sql(f"SELECT COUNT(*) FROM samples.tpch.{t.tableName}").collect()[0][0]
        print(f"  {t.tableName}: {count:,} rows")

    # Clone the data
    for t in tables:
        table_name = t.tableName
        if table_name not in ['region', 'nation']:  # Already created
            print(f"\nCloning {table_name}...")
            spark.sql(f"""
                CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.{table_name}
                AS SELECT * FROM samples.tpch.{table_name}
            """)
            count = spark.table(f"{CATALOG}.{SCHEMA}.{table_name}").count()
            print(f"✓ {table_name}: {count:,} rows")

except Exception as e:
    print(f"⚠️  samples.tpch not available: {e}")
    print("\nTo generate TPC-H data:")
    print("1. Use official dbgen tool from TPC.org")
    print("2. Or contact Databricks for pre-generated datasets")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

# List all tables
print("\n📊 Final tables in", f"{CATALOG}.{SCHEMA}:")
tables = spark.sql(f"SHOW TABLES IN {CATALOG}.{SCHEMA}").collect()
for t in tables:
    count = spark.table(f"{CATALOG}.{SCHEMA}.{t.tableName}").count()
    print(f"  {t.tableName}: {count:,} rows")
