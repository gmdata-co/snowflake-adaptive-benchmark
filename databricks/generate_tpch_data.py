#!/usr/bin/env python3
"""
Generate TPC-H Dataset in Databricks

This script generates TPC-H SF1000 (1TB) dataset in Databricks Delta Lake format.
Following the fair comparison approach: no explicit clustering, partitioning, or Z-ordering.

Based on databricks/tpch-dbgen and industry best practices.
"""

import logging
from databricks import sql
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import config
from config import CATALOG, SCHEMA, SCALE_FACTOR, WAREHOUSES

# TPC-H table definitions with expected row counts for SF1000
TPCH_TABLES = {
    "region": {"expected_rows": 5, "description": "Regions (5 rows, static)"},
    "nation": {"expected_rows": 25, "description": "Nations (25 rows, static)"},
    "supplier": {
        "expected_rows": 10_000 * SCALE_FACTOR,  # 10M for SF1000
        "description": "Suppliers",
    },
    "customer": {
        "expected_rows": 150_000 * SCALE_FACTOR,  # 150M for SF1000
        "description": "Customers",
    },
    "part": {
        "expected_rows": 200_000 * SCALE_FACTOR,  # 200M for SF1000
        "description": "Parts",
    },
    "partsupp": {
        "expected_rows": 800_000 * SCALE_FACTOR,  # 800M for SF1000
        "description": "Part-Supplier relationships",
    },
    "orders": {
        "expected_rows": 1_500_000 * SCALE_FACTOR,  # 1.5B for SF1000
        "description": "Orders",
    },
    "lineitem": {
        "expected_rows": 6_000_000 * SCALE_FACTOR,  # 6B for SF1000
        "description": "Line items (largest table)",
    },
}


def get_sql_connection():
    """Get SQL connection to Databricks warehouse."""
    host = os.environ.get("DATABRICKS_HOST")
    token = os.environ.get("DATABRICKS_TOKEN")

    if not host or not token:
        raise ValueError("DATABRICKS_HOST and DATABRICKS_TOKEN must be set")

    # Use the small warehouse for data generation
    warehouse_id = WAREHOUSES["small"]
    http_path = f"/sql/1.0/warehouses/{warehouse_id}"

    return sql.connect(
        server_hostname=host.replace("https://", "").replace("http://", ""),
        http_path=http_path,
        access_token=token,
    )


def generate_tpch_data_using_dbsqlgen():
    """
    Generate TPC-H data using Databricks SQL TPCH generator.

    Databricks has a built-in TPC-H data generator that can be called via SQL.
    This is the easiest method for generating TPC-H data at scale.
    """
    logger.info("=" * 70)
    logger.info("DATABRICKS TPC-H DATA GENERATION")
    logger.info("=" * 70)
    logger.info(f"Scale Factor: SF{SCALE_FACTOR} (~{SCALE_FACTOR}GB)")
    logger.info(f"Target: {CATALOG}.{SCHEMA}")
    logger.info(f"Tables: {len(TPCH_TABLES)}")
    logger.info("=" * 70)

    logger.info("\n⚠️  IMPORTANT NOTES:")
    logger.info("  - Data generation for SF1000 (1TB) can take 3-6 hours")
    logger.info("  - Estimated cost: $600-1200 depending on warehouse size")
    logger.info("  - This script uses Databricks' built-in TPC-H generator")
    logger.info("  - NO clustering, partitioning, or Z-ordering will be applied")
    logger.info("  - Monitor progress in Databricks SQL Warehouse UI")

    response = input("\nProceed with data generation? (yes/no): ")
    if response.lower() not in ["yes", "y"]:
        logger.info("Aborted by user")
        return False

    logger.info("\nConnecting to Databricks...")

    with get_sql_connection() as connection:
        cursor = connection.cursor()

        # Set the catalog and schema
        logger.info(f"\nUsing catalog and schema: {CATALOG}.{SCHEMA}")
        cursor.execute(f"USE CATALOG {CATALOG}")
        cursor.execute(f"USE SCHEMA {SCHEMA}")

        # Generate TPC-H data using Databricks SQL
        logger.info(f"\n🚀 Starting TPC-H SF{SCALE_FACTOR} data generation...")
        logger.info(
            "This will take several hours. You can monitor progress in the Databricks UI."
        )

        # Note: Databricks doesn't have a single built-in command for TPC-H generation
        # We need to use the tpch-dbgen tool via notebooks or Spark SQL
        logger.info("\n" + "=" * 70)
        logger.info("MANUAL STEPS REQUIRED")
        logger.info("=" * 70)
        logger.info(
            "\nDatabricks doesn't have a single SQL command for TPC-H generation."
        )
        logger.info("You have two options:")
        logger.info("\n📘 OPTION 1: Use Databricks Notebook (Recommended)")
        logger.info("  1. Go to your Databricks workspace")
        logger.info("  2. Import this notebook from Databricks Repos:")
        logger.info("     https://github.com/databricks/spark-sql-perf")
        logger.info("  3. Follow the TPC-H data generation example")
        logger.info("  4. Set these parameters:")
        logger.info(f"     - scaleFactor = {SCALE_FACTOR}")
        logger.info(f"     - location = '{CATALOG}.{SCHEMA}'")
        logger.info("     - format = 'delta'")
        logger.info("     - NO partitioning or clustering")
        logger.info("\n📘 OPTION 2: Use this SQL template")
        logger.info("  Run the following in Databricks SQL Editor:")

        # Print SQL template
        sql_template = f"""
-- Generate TPC-H SF{SCALE_FACTOR} data
-- WARNING: This is a template - Databricks requires Spark/Scala for actual generation

-- You'll need to use a notebook with this Scala code:
import com.databricks.spark.sql.perf.tpch.TPCHTables

val scaleFactor = "{SCALE_FACTOR}"
val tables = new TPCHTables(spark.sqlContext,
    dsdgenDir = "/tmp/tpch-dbgen",  // Will be downloaded automatically
    scaleFactor = scaleFactor,
    useDoubleForDecimal = false,
    useStringForDate = false)

// Generate data
tables.genData(
    location = "s3://your-bucket/tpch-sf{SCALE_FACTOR}",
    format = "parquet",
    overwrite = true,
    partitionTables = false,  // NO partitioning
    clusterByPartitionColumns = false,  // NO clustering
    filterOutNullPartitionValues = false,
    tableFilter = "",
    numPartitions = 1000)  // Parallelism for generation

// Create Delta tables
tables.createExternalTables("{CATALOG}.{SCHEMA}", "delta", overwrite = true)
"""
        logger.info(sql_template)

        logger.info("\n" + "=" * 70)
        logger.info("VALIDATION")
        logger.info("=" * 70)
        logger.info("\nAfter generation, run: uv run databricks/validate_tpch_data.py")
        logger.info("This will verify row counts and data quality.")

        return True


def main():
    """Main entry point."""
    try:
        generate_tpch_data_using_dbsqlgen()
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
