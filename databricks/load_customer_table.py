#!/usr/bin/env python3
"""Simple script to load customer table from S3 into Databricks."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from databricks import sql
from common.connections import DatabricksConnection
from config import DATABRICKS_HOST, DATABRICKS_TOKEN, CATALOG, SCHEMA, WAREHOUSES

# Initialize centralized logging
from common.logging_config import get_logger

logger = get_logger(__name__)

S3_PATH = "s3://snowflake-databricks-benchmarks-benchmarks-1763063895/customer/"


def main():
    logger.info("=" * 70)
    logger.info("LOADING CUSTOMER TABLE")
    logger.info("=" * 70)
    logger.info(f"\nS3 Path: {S3_PATH}")
    logger.info(f"Target:  {CATALOG}.{SCHEMA}.customer\n")

    # Connect
    logger.info("Connecting to Databricks...")
    conn_obj = DatabricksConnection(
        host=DATABRICKS_HOST,
        token=DATABRICKS_TOKEN,
        warehouse_id=WAREHOUSES["small"],
        catalog=CATALOG,
        schema=SCHEMA,
    )
    conn_obj.connect()
    cursor = conn_obj.connection.cursor()

    try:
        # Drop existing table
        logger.info("Dropping existing table...")
        cursor.execute(f"DROP TABLE IF EXISTS {CATALOG}.{SCHEMA}.customer")

        # Try COPY INTO with S3 path
        logger.info("Loading data from S3 using COPY INTO...")
        sql_cmd = f"""
        COPY INTO {CATALOG}.{SCHEMA}.customer
        FROM (
            SELECT * FROM read_parquet('{S3_PATH}')
        )
        FILEFORMAT = PARQUET
        """
        try:
            cursor.execute(sql_cmd)
            logger.info("✅ Table created with COPY INTO")
        except Exception as e:
            logger.info(f"COPY INTO failed: {e}")
            logger.info("Trying alternative approach...")
            # Fallback: create external table first
            sql_cmd = f"""
            CREATE EXTERNAL TABLE {CATALOG}.{SCHEMA}.customer
            USING PARQUET
            LOCATION '{S3_PATH}'
            """
            cursor.execute(sql_cmd)
            logger.info("✅ External table created")

        # Verify
        logger.info("\nVerifying...")
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {CATALOG}.{SCHEMA}.customer")
        result = cursor.fetchone()
        count = result[0] if result else 0
        logger.info(f"✅ {count:,} rows loaded")

        logger.info("\n" + "=" * 70)
        logger.info("✅ SUCCESS")
        logger.info("=" * 70)
        return True

    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        return False
    finally:
        cursor.close()
        conn_obj.disconnect()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
