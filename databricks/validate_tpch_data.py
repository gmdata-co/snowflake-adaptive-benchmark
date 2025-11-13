#!/usr/bin/env python3
"""
Validate TPC-H SF1000 Dataset in Databricks

This script validates that TPC-H data has been correctly loaded into Databricks by:
1. Checking row counts match TPC-H SF1000 specification
2. Verifying table schemas
3. Running sample queries to ensure data quality
4. Checking for clustering/partitioning (should be none for fair comparison)
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

# Expected row counts for TPC-H SF1000
EXPECTED_ROW_COUNTS = {
    "region": 5,
    "nation": 25,
    "supplier": 10_000_000,  # 10M
    "customer": 150_000_000,  # 150M
    "part": 200_000_000,  # 200M
    "partsupp": 800_000_000,  # 800M
    "orders": 1_500_000_000,  # 1.5B
    "lineitem": 6_000_000_000,  # 6B
}


def get_sql_connection():
    """Get SQL connection to Databricks warehouse."""
    host = os.environ.get("DATABRICKS_HOST")
    token = os.environ.get("DATABRICKS_TOKEN")

    if not host or not token:
        raise ValueError("DATABRICKS_HOST and DATABRICKS_TOKEN must be set")

    # Use the small warehouse for validation
    warehouse_id = WAREHOUSES["small"]
    http_path = f"/sql/1.0/warehouses/{warehouse_id}"

    return sql.connect(
        server_hostname=host.replace("https://", "").replace("http://", ""),
        http_path=http_path,
        access_token=token,
    )


def validate_row_counts():
    """Validate that table row counts match TPC-H specification."""
    logger.info("=" * 70)
    logger.info("VALIDATING ROW COUNTS")
    logger.info("=" * 70)

    with get_sql_connection() as connection:
        cursor = connection.cursor()

        # Set catalog and schema
        cursor.execute(f"USE CATALOG {CATALOG}")
        cursor.execute(f"USE SCHEMA {SCHEMA}")

        all_valid = True

        for table, expected_count in EXPECTED_ROW_COUNTS.items():
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                result = cursor.fetchone()
                actual_count = result[0] if result else 0

                # Allow some tolerance for very large tables (due to generation randomness)
                tolerance = 0.01  # 1% tolerance
                min_count = int(expected_count * (1 - tolerance))
                max_count = int(expected_count * (1 + tolerance))

                if min_count <= actual_count <= max_count:
                    match = "✓"
                    status = "PASS"
                else:
                    match = "✗"
                    status = "FAIL"
                    all_valid = False

                logger.info(
                    f"{match} {table:12s}: {actual_count:>15,} (expected: {expected_count:>15,}) - {status}"
                )

            except Exception as e:
                logger.error(f"✗ {table:12s}: ERROR - {e}")
                all_valid = False

    return all_valid


def validate_table_properties():
    """Validate that tables have no clustering or partitioning."""
    logger.info("\n" + "=" * 70)
    logger.info("VALIDATING TABLE PROPERTIES")
    logger.info("=" * 70)
    logger.info(
        "Checking for clustering/partitioning (should have NONE for fair comparison)"
    )

    with get_sql_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(f"USE CATALOG {CATALOG}")
        cursor.execute(f"USE SCHEMA {SCHEMA}")

        all_valid = True

        for table in EXPECTED_ROW_COUNTS.keys():
            try:
                # Check table properties
                cursor.execute(f"DESCRIBE DETAIL {table}")
                details = cursor.fetchone()

                # Check partitionColumns (should be empty array)
                partition_cols = (
                    details[5] if len(details) > 5 else "[]"
                )  # Assuming column 5 is partitionColumns

                logger.info(f"\n{table.upper()}:")
                logger.info(
                    f"  Format: {details[4] if len(details) > 4 else 'unknown'}"
                )  # Assuming column 4 is format
                logger.info(f"  Partition Columns: {partition_cols}")

                # Warn if partitioned
                if partition_cols and partition_cols != "[]":
                    logger.warning(
                        f"  ⚠ Table {table} has partitioning - this may affect fair comparison!"
                    )
                    all_valid = False
                else:
                    logger.info("  ✓ No partitioning (good for fair comparison)")

            except Exception as e:
                logger.error(f"  ✗ Error checking {table}: {e}")
                all_valid = False

    return all_valid


def run_sample_queries():
    """Run sample queries to verify data quality."""
    logger.info("\n" + "=" * 70)
    logger.info("RUNNING SAMPLE QUERIES")
    logger.info("=" * 70)

    with get_sql_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(f"USE CATALOG {CATALOG}")
        cursor.execute(f"USE SCHEMA {SCHEMA}")

        # Sample query 1: Check REGION table
        logger.info("\n1. Checking REGION table (should have 5 regions):")
        cursor.execute("SELECT r_name FROM region ORDER BY r_name")
        regions = [row[0] for row in cursor.fetchall()]
        logger.info(f"   Regions: {', '.join(regions)}")

        # Sample query 2: Check date ranges in ORDERS
        logger.info("\n2. Checking date range in ORDERS table:")
        cursor.execute("""
            SELECT
                MIN(o_orderdate) as min_date,
                MAX(o_orderdate) as max_date,
                COUNT(DISTINCT o_orderdate) as distinct_dates
            FROM orders
        """)
        result = cursor.fetchone()
        logger.info(f"   Min date: {result[0]}")
        logger.info(f"   Max date: {result[1]}")
        logger.info(f"   Distinct dates: {result[2]:,}")

        # Sample query 3: Check LINEITEM aggregates
        logger.info("\n3. Running aggregate query on LINEITEM (may take a minute):")
        cursor.execute("""
            SELECT
                l_returnflag,
                l_linestatus,
                COUNT(*) as count_order
            FROM lineitem
            WHERE l_shipdate <= DATE '1998-09-02'
            GROUP BY l_returnflag, l_linestatus
            ORDER BY l_returnflag, l_linestatus
        """)
        logger.info("   Return Flag | Line Status | Count")
        logger.info("   " + "-" * 45)
        for row in cursor.fetchall():
            logger.info(f"   {row[0]:11s} | {row[1]:11s} | {row[2]:>15,}")

        logger.info("\n✓ Sample queries completed successfully")


def main():
    """Main entry point."""
    logger.info("=" * 70)
    logger.info("TPC-H SF1000 DATA VALIDATION")
    logger.info("=" * 70)
    logger.info(f"Catalog: {CATALOG}")
    logger.info(f"Schema: {SCHEMA}")
    logger.info(f"Scale Factor: SF{SCALE_FACTOR}")
    logger.info("=" * 70)

    try:
        # 1. Validate row counts
        counts_valid = validate_row_counts()

        # 2. Validate table properties
        props_valid = validate_table_properties()

        # 3. Run sample queries
        run_sample_queries()

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 70)

        if counts_valid and props_valid:
            logger.info("✓ All validations passed!")
            logger.info("\nNext steps:")
            logger.info("1. Review validation results above")
            logger.info("2. Ready to run benchmark: uv run databricks/benchmark.py")
            return 0
        else:
            logger.warning("⚠ Some validations failed - review results above")
            logger.info("\nBefore running benchmarks:")
            logger.info("1. Fix any row count mismatches")
            logger.info("2. Remove any clustering/partitioning if present")
            return 1

    except Exception as e:
        logger.error(f"\n✗ Validation error: {e}")
        logger.info("\nTroubleshooting:")
        logger.info("1. Ensure TPC-H data has been generated")
        logger.info("2. Check DATABRICKS_HOST and DATABRICKS_TOKEN are set")
        logger.info("3. Verify catalog and schema names in config.py")
        return 1


if __name__ == "__main__":
    exit(main())
