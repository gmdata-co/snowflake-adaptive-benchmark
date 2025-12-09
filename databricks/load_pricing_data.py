#!/usr/bin/env python3
"""
Load Databricks Pricing Data from system.billing.list_prices to DuckDB

Queries the Databricks system billing table to get current serverless SQL compute
pricing and stores it in DuckDB for cost calculations.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
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


class PricingDataLoader:
    """Loads Databricks pricing data into DuckDB."""

    def __init__(self):
        """Initialize loader."""
        self.duckdb_path = DUCKDB_PATH
        self.db_conn = None

    def connect(self):
        """Establish connection to Databricks."""
        logger.info("Connecting to Databricks to query pricing data...")

        warehouse_id = WAREHOUSES.get("admin")
        if not warehouse_id:
            raise ValueError("Admin warehouse not configured in .env file (DATABRICKS_ADMIN_WAREHOUSE)")

        logger.info(f"  Using warehouse: {warehouse_id}")

        self.db_conn = DatabricksConnection(
            host=DATABRICKS_HOST,
            token=DATABRICKS_TOKEN,
            warehouse_id=warehouse_id,
            catalog=CATALOG,
            schema="benchmark",
        )

        self.db_conn.connect()
        logger.info("✅ Connected to Databricks")

    def disconnect(self):
        """Close connection."""
        if self.db_conn:
            self.db_conn.disconnect()
            logger.info("✅ Disconnected from Databricks")

    def fetch_serverless_pricing(self) -> List[Dict[str, Any]]:
        """
        Fetch current serverless SQL compute pricing from system.billing.list_prices.

        Returns:
            List of pricing records
        """
        logger.info("\nFetching serverless SQL compute pricing...")

        query = """
        SELECT
            sku_name,
            cloud,
            usage_unit,
            pricing.default AS price_per_unit,
            pricing.promotional.default AS promotional_price,
            pricing.effective_list.default AS effective_price,
            currency_code,
            price_start_time,
            price_end_time,
            account_id
        FROM system.billing.list_prices
        WHERE sku_name LIKE '%SERVERLESS_SQL_COMPUTE%'
            AND pricing.default IS NOT NULL
            AND price_end_time IS NULL  -- Only current prices
        ORDER BY sku_name, cloud
        """

        cursor = self.db_conn.execute_query(query)

        logger.info("  Fetching results...")
        results = cursor.fetchall()
        cursor.close()

        logger.info(f"✅ Retrieved {len(results)} pricing records")

        # Convert to list of dicts
        pricing_data = []
        for row in results:
            pricing_data.append({
                'sku_name': row[0],
                'cloud': row[1],
                'usage_unit': row[2],
                'price_per_unit': float(row[3]) if row[3] is not None else None,
                'promotional_price': float(row[4]) if row[4] is not None else None,
                'effective_price': float(row[5]) if row[5] is not None else None,
                'currency_code': row[6],
                'price_start_time': row[7],
                'price_end_time': row[8],
                'account_id': row[9],
            })

        return pricing_data

    def create_pricing_table(self):
        """Create pricing table in DuckDB if it doesn't exist."""
        logger.info("\nCreating pricing table in DuckDB...")

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS databricks_pricing (
            sku_name VARCHAR,
            cloud VARCHAR,
            usage_unit VARCHAR,
            price_per_unit DOUBLE,
            promotional_price DOUBLE,
            effective_price DOUBLE,
            currency_code VARCHAR,
            price_start_time TIMESTAMP,
            price_end_time TIMESTAMP,
            account_id VARCHAR,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        conn = duckdb.connect(str(self.duckdb_path))
        try:
            conn.execute(create_table_sql)
            conn.commit()
            logger.info("✅ Pricing table ready")
        finally:
            conn.close()

    def load_pricing_data(self, pricing_data: List[Dict[str, Any]]):
        """
        Load pricing data into DuckDB.

        Args:
            pricing_data: List of pricing records to load
        """
        if not pricing_data:
            logger.warning("No pricing data to load")
            return

        logger.info(f"\nLoading {len(pricing_data)} pricing records into DuckDB...")

        conn = duckdb.connect(str(self.duckdb_path))
        try:
            # Clear existing data
            conn.execute("DELETE FROM databricks_pricing")
            logger.info("  Cleared existing pricing data")

            # Insert new data
            insert_sql = """
            INSERT INTO databricks_pricing (
                sku_name,
                cloud,
                usage_unit,
                price_per_unit,
                promotional_price,
                effective_price,
                currency_code,
                price_start_time,
                price_end_time,
                account_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            for record in pricing_data:
                conn.execute(insert_sql, [
                    record['sku_name'],
                    record['cloud'],
                    record['usage_unit'],
                    record['price_per_unit'],
                    record['promotional_price'],
                    record['effective_price'],
                    record['currency_code'],
                    record['price_start_time'],
                    record['price_end_time'],
                    record['account_id'],
                ])

            conn.commit()
            logger.info(f"✅ Loaded {len(pricing_data)} pricing records")
        finally:
            conn.close()

    def print_summary(self, pricing_data: List[Dict[str, Any]]):
        """Print summary of loaded pricing data."""
        logger.info("\n" + "=" * 80)
        logger.info("PRICING DATA SUMMARY")
        logger.info("=" * 80)

        # Group by SKU type
        enterprise_count = sum(1 for p in pricing_data if 'ENTERPRISE' in p['sku_name'])
        premium_count = sum(1 for p in pricing_data if 'PREMIUM' in p['sku_name'])
        standard_count = sum(1 for p in pricing_data if 'STANDARD' in p['sku_name'])

        logger.info(f"Total pricing records: {len(pricing_data)}")
        logger.info(f"  Enterprise SKUs: {enterprise_count}")
        logger.info(f"  Premium SKUs: {premium_count}")
        logger.info(f"  Standard SKUs: {standard_count}")

        # Show sample prices
        logger.info("\nSample pricing (USD per DBU):")
        for record in pricing_data[:5]:
            price = record['price_per_unit']
            logger.info(f"  {record['sku_name']}: ${price:.2f}")

        logger.info("=" * 80)


def main():
    """Main entry point."""
    loader = PricingDataLoader()

    try:
        # Connect to Databricks
        loader.connect()

        # Fetch pricing data
        pricing_data = loader.fetch_serverless_pricing()

        # Disconnect from Databricks (we're done querying)
        loader.disconnect()

        # Create table in DuckDB
        loader.create_pricing_table()

        # Load data into DuckDB
        loader.load_pricing_data(pricing_data)

        # Print summary
        loader.print_summary(pricing_data)

        logger.info("\n✅ Pricing data loaded successfully!")
        return 0

    except Exception as e:
        import traceback
        logger.error(f"\n❌ Failed to load pricing data: {e}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return 1

    finally:
        loader.disconnect()


if __name__ == "__main__":
    exit(main())
