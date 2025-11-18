"""
Snowflake Warehouse Usage Loader

Fetches warehouse credit usage from SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
and loads it into DuckDB for cost analysis.
"""

import sys
from pathlib import Path
from typing import Set, List, Dict, Any
from datetime import datetime
import duckdb

# Add parent directory to path for common imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.logging_config import get_logger
from common.connections.snowflake_connection import SnowflakeConnection
from config import (
    SNOWFLAKE_CONNECTION,
    SNOWFLAKE_ROLE,
    SNOWFLAKE_DATABASE,
    SNOWFLAKE_SCHEMA,
    DUCKDB_PATH,
)

logger = get_logger(__name__)


class WarehouseUsageLoader:
    """Loads Snowflake warehouse usage data into DuckDB."""

    def __init__(self):
        """Initialize loader."""
        self.duckdb_path = DUCKDB_PATH
        self.sf_conn = None

    def connect(self):
        """Establish connection to Snowflake."""
        logger.info("Connecting to Snowflake to query warehouse usage...")

        self.sf_conn = SnowflakeConnection(
            connection_name=SNOWFLAKE_CONNECTION,
            role=SNOWFLAKE_ROLE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA
        )
        self.sf_conn.connect()
        logger.info("✅ Connected to Snowflake")

    def disconnect(self):
        """Close Snowflake connection."""
        if self.sf_conn:
            self.sf_conn.disconnect()
            logger.info("✅ Disconnected from Snowflake")

    def get_warehouse_names_from_duckdb(self) -> Set[str]:
        """
        Get unique warehouse names from snowflake_results table.

        Returns:
            Set of warehouse names

        Raises:
            Exception: If DuckDB cannot be accessed
        """
        logger.info("\nFetching warehouse names from DuckDB...")

        conn = duckdb.connect(str(self.duckdb_path), read_only=True)
        try:
            # Query distinct warehouse names from snowflake_results
            result = conn.execute("""
                SELECT DISTINCT warehouse_name
                FROM snowflake_results
                WHERE warehouse_name IS NOT NULL
                ORDER BY warehouse_name
            """).fetchall()

            warehouse_names = set(row[0] for row in result)
            logger.info(f"✅ Found {len(warehouse_names)} unique warehouses from DuckDB")
            for wh_name in sorted(warehouse_names):
                logger.info(f"  - {wh_name}")

            return warehouse_names
        finally:
            conn.close()

    def get_earliest_timestamp_from_duckdb(self) -> datetime:
        """
        Get the earliest timestamp from snowflake_results table.

        Returns:
            Earliest timestamp from benchmark runs

        Raises:
            Exception: If DuckDB cannot be accessed or no timestamps found
        """
        logger.info("\nFetching earliest benchmark timestamp from DuckDB...")

        conn = duckdb.connect(str(self.duckdb_path), read_only=True)
        try:
            result = conn.execute("""
                SELECT MIN(timestamp) as min_ts
                FROM snowflake_results
            """).fetchone()

            if result and result[0]:
                min_ts = result[0]
                logger.info(f"✅ Earliest benchmark timestamp: {min_ts}")
                return min_ts
            else:
                raise ValueError("No timestamps found in snowflake_results")
        finally:
            conn.close()

    def fetch_warehouse_usage(
        self,
        warehouse_names: Set[str],
        start_time: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Fetch warehouse credit usage from Snowflake ACCOUNT_USAGE.

        Args:
            warehouse_names: Set of warehouse names to fetch usage for
            start_time: Start time for usage query

        Returns:
            List of usage records
        """
        if not warehouse_names:
            logger.warning("No warehouse names provided")
            return []

        logger.info("\nFetching warehouse usage from Snowflake...")
        logger.info(f"  Warehouses: {len(warehouse_names)}")
        logger.info(f"  Start time: {start_time}")

        # Build warehouse name list for SQL IN clause
        warehouse_list = "','".join(warehouse_names)

        # Query ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        # This table has hourly aggregated data with ~2 hour latency
        query = f"""
        SELECT
            WAREHOUSE_NAME,
            START_TIME,
            END_TIME,
            CREDITS_USED as total_credits,
            CREDITS_USED_COMPUTE as compute_credits,
            CREDITS_USED_CLOUD_SERVICES as cloud_services_credits
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        WHERE WAREHOUSE_NAME IN ('{warehouse_list}')
            AND START_TIME >= '{start_time.isoformat()}'
        ORDER BY WAREHOUSE_NAME, START_TIME
        """

        logger.info("Executing query on SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY...")
        cursor = self.sf_conn.execute_query(query)
        rows = cursor.fetchall()

        logger.info(f"✅ Retrieved {len(rows)} usage records")

        # Convert to list of dicts
        usage_data = []
        total_credits = 0.0

        for row in rows:
            record = {
                'warehouse_name': row[0],
                'start_time': row[1],
                'end_time': row[2],
                'total_credits': float(row[3]) if row[3] else 0.0,
                'compute_credits': float(row[4]) if row[4] else 0.0,
                'cloud_services_credits': float(row[5]) if row[5] else 0.0,
            }
            usage_data.append(record)
            total_credits += record['total_credits']

        # Log summary
        unique_warehouses = set(r['warehouse_name'] for r in usage_data)
        logger.info("\nUsage Summary:")
        logger.info(f"  Total records: {len(usage_data)}")
        logger.info(f"  Unique warehouses: {len(unique_warehouses)}")
        logger.info(f"  Total credits: {total_credits:.2f}")
        logger.info(f"  Estimated cost ($3/credit): ${total_credits * 3:.2f}")

        return usage_data

    def create_usage_table(self):
        """Create or replace the snowflake_wh_usage table in DuckDB."""
        logger.info("\nPreparing DuckDB table for warehouse usage...")

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS snowflake_wh_usage (
            warehouse_name VARCHAR,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            total_credits DECIMAL(38,9),
            compute_credits DECIMAL(38,9),
            cloud_services_credits DECIMAL(38,9),
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
        Load warehouse usage data into DuckDB.

        Args:
            usage_data: List of usage records to load
        """
        if not usage_data:
            logger.warning("No usage data to load")
            return

        logger.info(f"\nLoading {len(usage_data)} usage records into DuckDB...")

        conn = duckdb.connect(str(self.duckdb_path))
        try:
            # Clear existing data (idempotent)
            conn.execute("DELETE FROM snowflake_wh_usage")
            logger.info("  Cleared existing usage data")

            # Insert new data
            insert_sql = """
            INSERT INTO snowflake_wh_usage (
                warehouse_name,
                start_time,
                end_time,
                total_credits,
                compute_credits,
                cloud_services_credits
            ) VALUES (?, ?, ?, ?, ?, ?)
            """

            for record in usage_data:
                conn.execute(insert_sql, [
                    record['warehouse_name'],
                    record['start_time'],
                    record['end_time'],
                    record['total_credits'],
                    record['compute_credits'],
                    record['cloud_services_credits'],
                ])

            conn.commit()
            logger.info(f"✅ Loaded {len(usage_data)} usage records")
        finally:
            conn.close()

    def print_summary(self, usage_data: List[Dict[str, Any]]):
        """Print summary of loaded usage data."""
        logger.info("\n" + "=" * 80)
        logger.info("WAREHOUSE USAGE SUMMARY")
        logger.info("=" * 80)

        # Group by warehouse
        warehouse_totals = {}
        for record in usage_data:
            wh_name = record['warehouse_name']
            if wh_name not in warehouse_totals:
                warehouse_totals[wh_name] = {
                    'records': 0,
                    'total_credits': 0.0,
                    'compute_credits': 0.0,
                    'cloud_services_credits': 0.0,
                }
            warehouse_totals[wh_name]['records'] += 1
            warehouse_totals[wh_name]['total_credits'] += record['total_credits']
            warehouse_totals[wh_name]['compute_credits'] += record['compute_credits']
            warehouse_totals[wh_name]['cloud_services_credits'] += record['cloud_services_credits']

        # Print by warehouse
        for wh_name in sorted(warehouse_totals.keys()):
            totals = warehouse_totals[wh_name]
            logger.info(f"\n{wh_name}:")
            logger.info(f"  Records: {totals['records']}")
            logger.info(f"  Total credits: {totals['total_credits']:.4f}")
            logger.info(f"  Compute credits: {totals['compute_credits']:.4f}")
            logger.info(f"  Cloud services credits: {totals['cloud_services_credits']:.4f}")
            logger.info(f"  Estimated cost ($3/credit): ${totals['total_credits'] * 3:.2f}")

        # Grand total
        grand_total_credits = sum(t['total_credits'] for t in warehouse_totals.values())
        grand_total_cost = grand_total_credits * 3

        logger.info("\n" + "-" * 80)
        logger.info("GRAND TOTAL:")
        logger.info(f"  Total warehouses: {len(warehouse_totals)}")
        logger.info(f"  Total records: {len(usage_data)}")
        logger.info(f"  Total credits: {grand_total_credits:.4f}")
        logger.info(f"  Estimated cost ($3/credit): ${grand_total_cost:.2f}")
        logger.info("=" * 80 + "\n")


def main():
    """Main entry point."""
    loader = WarehouseUsageLoader()

    try:
        # Get warehouse names from DuckDB
        try:
            warehouse_names = loader.get_warehouse_names_from_duckdb()
        except Exception as e:
            if "lock" in str(e).lower():
                logger.error("❌ DuckDB is locked by another process")
                logger.error("Please close DBeaver or other database tools and try again")
            raise

        if not warehouse_names:
            logger.warning("No warehouses found in snowflake_results table")
            logger.info("Please run a benchmark first to generate results")
            return 1

        # Get earliest timestamp from DuckDB
        try:
            start_time = loader.get_earliest_timestamp_from_duckdb()
        except Exception as e:
            if "lock" in str(e).lower():
                logger.error("❌ DuckDB is locked by another process")
                logger.error("Please close DBeaver or other database tools and try again")
            raise

        # Connect to Snowflake
        loader.connect()

        # Fetch usage data
        usage_data = loader.fetch_warehouse_usage(warehouse_names, start_time)

        # Disconnect from Snowflake (we're done querying)
        loader.disconnect()

        if not usage_data:
            logger.warning("No usage data retrieved from Snowflake")
            logger.info("This could mean:")
            logger.info("  1. The warehouses haven't been used yet")
            logger.info("  2. The ACCOUNT_USAGE data hasn't been aggregated yet (up to 2 hour latency)")
            logger.info("  3. The start_time is too recent")
            return 1

        # Create table if needed
        loader.create_usage_table()

        # Load data into DuckDB
        loader.load_usage_data(usage_data)

        # Print summary
        loader.print_summary(usage_data)

        logger.info("✅ Warehouse usage loading complete!")
        return 0

    except Exception as e:
        logger.error(f"❌ Error loading warehouse usage: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
