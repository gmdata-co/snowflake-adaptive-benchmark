#!/usr/bin/env python3
"""
Load Databricks Warehouse Usage Data from system.billing.usage to DuckDB

Queries the Databricks system billing table to get warehouse usage metrics
(DBUs consumed) for warehouses used in the benchmark.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Set
from datetime import datetime, timedelta
import duckdb

# Add parent directory to path for common imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.logging_config import get_logger
from common.connections.databricks_connection import DatabricksConnection
from config import (
    DATABRICKS_HOST,
    DATABRICKS_TOKEN,
    CATALOG,
    DUCKDB_PATH,
    WAREHOUSES,
)

logger = get_logger(__name__)


class WarehouseUsageLoader:
    """Loads Databricks warehouse usage data into DuckDB."""

    def __init__(self):
        """Initialize loader."""
        self.duckdb_path = DUCKDB_PATH
        self.db_conn = None

    def connect(self):
        """Establish connection to Databricks."""
        logger.info("Connecting to Databricks to query warehouse usage data...")

        warehouse_id = WAREHOUSES.get("xsmall")
        if not warehouse_id:
            raise ValueError("XSMALL warehouse not configured in .env file")

        logger.info(f"  Using warehouse: {warehouse_id}")

        self.db_conn = DatabricksConnection(
            host=DATABRICKS_HOST,
            token=DATABRICKS_TOKEN,
            warehouse_id=warehouse_id,
            catalog=CATALOG,
            schema="benchmark",
        )

        self.db_conn.connect()

        # Switch to system catalog for querying system tables
        logger.info("  Switching to system catalog...")
        cursor = self.db_conn.get_cursor()
        cursor.execute("USE CATALOG system")
        cursor.close()
        logger.info("✅ Connected to Databricks system catalog")

    def disconnect(self):
        """Close connection."""
        if self.db_conn:
            self.db_conn.disconnect()
            logger.info("✅ Disconnected from Databricks")

    def get_warehouse_ids_from_duckdb(self) -> Set[str]:
        """
        Get unique warehouse IDs from databricks_results table.

        Returns:
            Set of warehouse IDs (warehouse_name column contains the warehouse ID)

        Raises:
            Exception: If DuckDB cannot be accessed
        """
        logger.info("\nFetching warehouse IDs from DuckDB...")

        conn = duckdb.connect(str(self.duckdb_path), read_only=True)
        try:
            # Query distinct warehouse IDs from databricks_results
            result = conn.execute("""
                SELECT DISTINCT warehouse_name
                FROM databricks_results
                WHERE warehouse_name IS NOT NULL
                ORDER BY warehouse_name
            """).fetchall()

            warehouse_ids = set(row[0] for row in result)
            logger.info(f"✅ Found {len(warehouse_ids)} unique warehouses from DuckDB")
            for wh_id in sorted(warehouse_ids):
                logger.info(f"  - {wh_id}")

            return warehouse_ids
        finally:
            conn.close()

    def get_time_range_from_duckdb(self) -> tuple[datetime, datetime]:
        """
        Get the time range of benchmark runs from DuckDB.

        Returns:
            Tuple of (min_timestamp, max_timestamp)

        Raises:
            Exception: If DuckDB cannot be accessed or no timestamps found
        """
        logger.info("\nFetching benchmark time range from DuckDB...")

        conn = duckdb.connect(str(self.duckdb_path), read_only=True)
        try:
            result = conn.execute("""
                SELECT
                    MIN(timestamp) as min_ts,
                    MAX(timestamp) as max_ts
                FROM databricks_results
            """).fetchone()

            if result and result[0] and result[1]:
                min_ts = result[0]
                max_ts = result[1]
                logger.info(f"✅ Benchmark time range: {min_ts} to {max_ts}")
                return min_ts, max_ts
            else:
                raise ValueError("No timestamps found in databricks_results")
        finally:
            conn.close()

    def fetch_warehouse_usage(
        self,
        warehouse_ids: Set[str],
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Fetch warehouse usage data from system.billing.usage.

        Args:
            warehouse_ids: Set of warehouse IDs to fetch usage for
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of usage records
        """
        if not warehouse_ids:
            logger.warning("No warehouse IDs provided")
            return []

        logger.info(f"\nFetching warehouse usage for {len(warehouse_ids)} warehouses...")

        # Add buffer to time range (billing data is typically hourly)
        start_buffer = start_time - timedelta(hours=2)
        end_buffer = end_time + timedelta(hours=2)

        logger.info(f"  Date range: {start_buffer.date()} to {end_buffer.date()}")

        # Build warehouse ID list for SQL IN clause
        warehouse_id_list = "', '".join(warehouse_ids)

        query = f"""
        SELECT
            usage_metadata.warehouse_id,
            usage_date,
            usage_start_time,
            usage_end_time,
            usage_quantity,
            usage_unit,
            billing_origin_product,
            sku_name,
            cloud
        FROM system.billing.usage
        WHERE usage_metadata.warehouse_id IN ('{warehouse_id_list}')
            AND usage_date >= DATE('{start_buffer.date()}')
            AND usage_date <= DATE('{end_buffer.date()}')
            AND usage_unit = 'DBU'
        ORDER BY usage_start_time, usage_metadata.warehouse_id
        """

        logger.info("  Executing query against system.billing.usage...")
        cursor = self.db_conn.get_cursor()
        cursor.execute(query)

        logger.info("  Fetching results...")
        results = cursor.fetchall()
        cursor.close()

        logger.info(f"✅ Retrieved {len(results)} usage records")

        # Convert to list of dicts
        usage_data = []
        for row in results:
            usage_data.append({
                'warehouse_id': row[0],
                'usage_date': row[1],
                'usage_start_time': row[2],
                'usage_end_time': row[3],
                'usage_quantity': float(row[4]) if row[4] is not None else None,
                'usage_unit': row[5],
                'billing_origin_product': row[6],
                'sku_name': row[7],
                'cloud': row[8],
            })

        return usage_data

    def create_usage_table(self):
        """Create warehouse usage table in DuckDB if it doesn't exist."""
        logger.info("\nCreating warehouse usage table in DuckDB...")

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS databricks_wh_usage (
            warehouse_id VARCHAR,
            usage_date DATE,
            usage_start_time TIMESTAMP,
            usage_end_time TIMESTAMP,
            usage_quantity DOUBLE,
            usage_unit VARCHAR,
            billing_origin_product VARCHAR,
            sku_name VARCHAR,
            cloud VARCHAR,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        conn = duckdb.connect(str(self.duckdb_path))
        try:
            conn.execute(create_table_sql)
            conn.commit()
            logger.info("✅ Warehouse usage table ready")
        finally:
            conn.close()

    def load_usage_data(self, usage_data: List[Dict[str, Any]]):
        """
        Load usage data into DuckDB.

        Args:
            usage_data: List of usage records to load
        """
        if not usage_data:
            logger.warning("No usage data to load")
            return

        logger.info(f"\nLoading {len(usage_data)} usage records into DuckDB...")

        conn = duckdb.connect(str(self.duckdb_path))
        try:
            # Clear existing data
            conn.execute("DELETE FROM databricks_wh_usage")
            logger.info("  Cleared existing usage data")

            # Insert new data
            insert_sql = """
            INSERT INTO databricks_wh_usage (
                warehouse_id,
                usage_date,
                usage_start_time,
                usage_end_time,
                usage_quantity,
                usage_unit,
                billing_origin_product,
                sku_name,
                cloud
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            for record in usage_data:
                conn.execute(insert_sql, [
                    record['warehouse_id'],
                    record['usage_date'],
                    record['usage_start_time'],
                    record['usage_end_time'],
                    record['usage_quantity'],
                    record['usage_unit'],
                    record['billing_origin_product'],
                    record['sku_name'],
                    record['cloud'],
                ])

            conn.commit()
            logger.info(f"✅ Loaded {len(usage_data)} usage records")
        finally:
            conn.close()

    def print_summary(self, usage_data: List[Dict[str, Any]]):
        """Print summary of loaded usage data."""
        logger.info("\n" + "=" * 80)
        logger.info("WAREHOUSE USAGE DATA SUMMARY")
        logger.info("=" * 80)

        # Calculate totals by warehouse
        warehouse_totals = {}
        for record in usage_data:
            wh_id = record['warehouse_id']
            if wh_id not in warehouse_totals:
                warehouse_totals[wh_id] = {
                    'total_dbu': 0.0,
                    'record_count': 0,
                }
            warehouse_totals[wh_id]['total_dbu'] += record['usage_quantity'] or 0.0
            warehouse_totals[wh_id]['record_count'] += 1

        logger.info(f"Total usage records: {len(usage_data)}")
        logger.info(f"Warehouses tracked: {len(warehouse_totals)}")
        logger.info("\nDBU consumption by warehouse:")

        for wh_id in sorted(warehouse_totals.keys()):
            stats = warehouse_totals[wh_id]
            logger.info(f"  {wh_id}:")
            logger.info(f"    Total DBUs: {stats['total_dbu']:.4f}")
            logger.info(f"    Usage periods: {stats['record_count']}")

        total_dbu = sum(wh['total_dbu'] for wh in warehouse_totals.values())
        logger.info(f"\nOverall total DBUs consumed: {total_dbu:.4f}")
        logger.info("=" * 80)


def main():
    """Main entry point."""
    loader = WarehouseUsageLoader()

    try:
        # Get warehouse IDs from DuckDB
        try:
            warehouse_ids = loader.get_warehouse_ids_from_duckdb()
        except Exception as e:
            if "lock" in str(e).lower():
                logger.error("❌ DuckDB is locked by another process")
                logger.error("Please close DBeaver or other database tools and try again")
            raise

        if not warehouse_ids:
            logger.warning("No warehouses found in databricks_results table")
            logger.info("Please run a benchmark first to generate results")
            return 1

        # Get time range from DuckDB
        try:
            start_time, end_time = loader.get_time_range_from_duckdb()
        except Exception as e:
            if "lock" in str(e).lower():
                logger.error("❌ DuckDB is locked by another process")
                logger.error("Please close DBeaver or other database tools and try again")
            raise

        # Connect to Databricks
        loader.connect()

        # Fetch usage data
        usage_data = loader.fetch_warehouse_usage(warehouse_ids, start_time, end_time)

        # Disconnect from Databricks (we're done querying)
        loader.disconnect()

        if not usage_data:
            logger.warning("No usage data found for the specified warehouses and time range")
            logger.info("Note: Billing data may have significant latency (hours to days)")
            return 1

        # Create table in DuckDB
        loader.create_usage_table()

        # Load data into DuckDB
        loader.load_usage_data(usage_data)

        # Print summary
        loader.print_summary(usage_data)

        logger.info("\n✅ Warehouse usage data loaded successfully!")
        return 0

    except Exception as e:
        import traceback
        logger.error(f"\n❌ Failed to load warehouse usage data: {e}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return 1

    finally:
        loader.disconnect()


if __name__ == "__main__":
    exit(main())
