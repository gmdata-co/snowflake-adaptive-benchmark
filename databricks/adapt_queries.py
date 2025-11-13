#!/usr/bin/env python3
"""
Adapt Snowflake TPC-H queries for Databricks

This script converts Snowflake TPC-H queries to Databricks syntax by:
1. Replacing Snowflake table references with Databricks catalog.schema.table
2. Adjusting SQL syntax differences between platforms
3. Converting to lowercase table names (Databricks convention)
"""

import re
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import config
from config import CATALOG, SCHEMA

# Source and destination directories
SNOWFLAKE_QUERIES_DIR = Path("../snowflake/queries/adapted_queries")
DATABRICKS_QUERIES_DIR = Path("queries")

# TPC-H table names
TPCH_TABLES = [
    "REGION",
    "NATION",
    "SUPPLIER",
    "CUSTOMER",
    "PART",
    "PARTSUPP",
    "ORDERS",
    "LINEITEM",
]


def adapt_query(snowflake_sql: str) -> str:
    """
    Adapt a Snowflake TPC-H query for Databricks.

    Args:
        snowflake_sql: Original Snowflake SQL query

    Returns:
        Adapted Databricks SQL query
    """
    databricks_sql = snowflake_sql

    # 1. Replace Snowflake table references with Databricks references
    # Pattern: SNOWFLAKE_SAMPLE_DATA.TPCH_SF<number>.<TABLE>
    # Replace with: catalog.schema.table (lowercase)

    for table in TPCH_TABLES:
        # Match patterns like: SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.LINEITEM
        # or TPCH_SF1000.LINEITEM
        pattern = rf"SNOWFLAKE_SAMPLE_DATA\.TPCH_SF\d+\.{table}"
        replacement = f"{CATALOG}.{SCHEMA}.{table.lower()}"
        databricks_sql = re.sub(
            pattern, replacement, databricks_sql, flags=re.IGNORECASE
        )

        # Also handle cases without SNOWFLAKE_SAMPLE_DATA prefix
        pattern = rf"TPCH_SF\d+\.{table}"
        replacement = f"{CATALOG}.{SCHEMA}.{table.lower()}"
        databricks_sql = re.sub(
            pattern, replacement, databricks_sql, flags=re.IGNORECASE
        )

    # 2. Interval syntax differences
    # Snowflake: INTERVAL '90 DAYS'
    # Databricks: INTERVAL 90 DAYS (no quotes around value)
    databricks_sql = re.sub(
        r"INTERVAL '(\d+) (DAY|DAYS|MONTH|MONTHS|YEAR|YEARS)'",
        r"INTERVAL \1 \2",
        databricks_sql,
        flags=re.IGNORECASE,
    )

    # 3. Date literals - both platforms use date '1998-12-01' syntax, so no change needed

    # 4. Add note about Databricks adaptation
    header_comment = f"""-- Adapted for Databricks from Snowflake TPC-H query
-- Catalog: {CATALOG}
-- Schema: {SCHEMA}
-- Scale Factor: SF1000 (1TB)
--
"""

    # Insert header after existing comments
    lines = databricks_sql.split("\n")
    # Find the last comment line
    last_comment_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("--"):
            last_comment_idx = i
        else:
            break

    # Insert adaptation note after last original comment
    lines.insert(last_comment_idx + 1, header_comment)
    databricks_sql = "\n".join(lines)

    return databricks_sql


def adapt_all_queries():
    """Adapt all Snowflake TPC-H queries for Databricks."""
    logger.info("=" * 70)
    logger.info("ADAPTING TPC-H QUERIES FOR DATABRICKS")
    logger.info("=" * 70)
    logger.info(f"Source: {SNOWFLAKE_QUERIES_DIR}")
    logger.info(f"Destination: {DATABRICKS_QUERIES_DIR}")
    logger.info(f"Target: {CATALOG}.{SCHEMA}")
    logger.info("=" * 70)

    # Ensure destination directory exists
    DATABRICKS_QUERIES_DIR.mkdir(exist_ok=True)

    # Process each query
    success_count = 0
    error_count = 0

    for i in range(1, 23):  # q01 through q22
        query_file = f"q{i:02d}.sql"
        source_path = SNOWFLAKE_QUERIES_DIR / query_file
        dest_path = DATABRICKS_QUERIES_DIR / query_file

        try:
            if not source_path.exists():
                logger.warning(f"⚠ Skipping {query_file}: source file not found")
                continue

            # Read Snowflake query
            with open(source_path, "r") as f:
                snowflake_sql = f.read()

            # Adapt for Databricks
            databricks_sql = adapt_query(snowflake_sql)

            # Write Databricks query
            with open(dest_path, "w") as f:
                f.write(databricks_sql)

            logger.info(f"✓ Adapted {query_file}")
            success_count += 1

        except Exception as e:
            logger.error(f"✗ Error adapting {query_file}: {e}")
            error_count += 1

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("ADAPTATION COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Successfully adapted: {success_count} queries")
    logger.info(f"Errors: {error_count} queries")

    if success_count > 0:
        logger.info(f"\n✓ Queries saved to: {DATABRICKS_QUERIES_DIR}")
        logger.info("\nNext steps:")
        logger.info("1. Review adapted queries for correctness")
        logger.info("2. Test a few queries against your Databricks data")
        logger.info("3. Run full benchmark with databricks/benchmark.py")


def main():
    """Main entry point."""
    adapt_all_queries()


if __name__ == "__main__":
    main()
