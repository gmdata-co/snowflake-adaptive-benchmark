#!/usr/bin/env python3
"""
Enrich Benchmark Results with ACCOUNT_USAGE Data

Queries SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY to get detailed metrics
for all unenriched queries in the DuckDB database.

NOTE: Run this script at least 45 minutes after the benchmark completes
to ensure ACCOUNT_USAGE has been populated.
"""

import argparse
import toml
import sys
from pathlib import Path
from typing import List, Dict, Any

import snowflake.connector
from snowflake.connector import DictCursor
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# Initialize centralized logging
sys.path.insert(0, str(Path(__file__).parent.parent))
from common.logging_config import get_logger
from common.storage import BenchmarkStorage
from config import (
    SNOWFLAKE_CONNECTION,
    SNOWFLAKE_ROLE,
    SNOWFLAKE_DATABASE,
    SNOWFLAKE_SCHEMA,
    DUCKDB_PATH,
)

logger = get_logger(__name__)


class ResultsEnricher:
    """Enriches benchmark results with ACCOUNT_USAGE data."""

    def __init__(self, connection_name: str = SNOWFLAKE_CONNECTION):
        """Initialize enricher."""
        self.connection_name = connection_name
        self.conn: snowflake.connector.SnowflakeConnection = None
        self.storage = BenchmarkStorage(DUCKDB_PATH)

    def _load_connection_config(self, connection_name: str) -> dict:
        """Load connection configuration from ~/.snowflake/connections.toml"""
        connections_file = Path.home() / ".snowflake" / "connections.toml"
        if not connections_file.exists():
            raise FileNotFoundError(
                f"Snowflake connections file not found: {connections_file}"
            )

        config = toml.load(connections_file)
        if connection_name not in config:
            raise ValueError(
                f"Connection '{connection_name}' not found in {connections_file}"
            )

        return config[connection_name]

    def _load_private_key(self, private_key_path: str):
        """Load and decode the private key for JWT authentication."""
        with open(private_key_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(), password=None, backend=default_backend()
            )

        return private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def connect(self):
        """Establish connection to Snowflake using the configured connection."""
        logger.info(f"Connecting to Snowflake using connection: {self.connection_name}")

        # Load connection configuration from ~/.snowflake/connections.toml
        conn_config = self._load_connection_config(self.connection_name)

        # Prepare connection parameters
        connect_params = {
            "account": conn_config["account"],
            "user": conn_config["user"],
            "role": SNOWFLAKE_ROLE,
            "database": SNOWFLAKE_DATABASE,
            "schema": SNOWFLAKE_SCHEMA,
        }

        # Handle JWT authentication if configured
        if conn_config.get("authenticator") == "SNOWFLAKE_JWT":
            private_key_path = conn_config.get("private_key_path") or conn_config.get(
                "private_key_file"
            )
            if private_key_path:
                connect_params["private_key"] = self._load_private_key(private_key_path)

        # Connect to Snowflake
        self.conn = snowflake.connector.connect(**connect_params)

        # Set warehouse for querying ACCOUNT_USAGE
        cursor = self.conn.cursor()
        cursor.execute("USE WAREHOUSE BENCHMARK_WH_MEDIUM")
        cursor.close()

        logger.info("✅ Connected to Snowflake")

    def disconnect(self):
        """Close connection."""
        if self.conn:
            self.conn.close()
            logger.info("✅ Disconnected from Snowflake")

    def get_unenriched_queries(self) -> List[Dict[str, Any]]:
        """
        Get all unenriched queries from DuckDB.

        Returns:
            List of query dictionaries with query_id and metadata
        """
        logger.info("\nFetching unenriched queries from DuckDB...")

        results = self.storage.query("""
            SELECT query_id, run_id, query_num, run_num
            FROM snowflake_results
            WHERE query_id IS NOT NULL
            AND query_id != ''
            AND compilation_time_ms IS NULL
            ORDER BY timestamp
        """)

        queries = []
        for row in results:
            queries.append({
                'query_id': row[0],
                'run_id': row[1],
                'query_num': row[2],
                'run_num': row[3],
            })

        logger.info(f"✅ Found {len(queries)} unenriched queries")
        return queries

    def get_query_history_data(self, query_ids: List[str]) -> Dict[str, Dict]:
        """
        Query ACCOUNT_USAGE.QUERY_HISTORY for detailed metrics.

        Args:
            query_ids: List of query IDs to fetch

        Returns:
            Dictionary mapping query_id to metrics
        """
        if not query_ids:
            logger.warning("Warning: No query IDs to fetch")
            return {}

        logger.info(
            f"\nQuerying ACCOUNT_USAGE.QUERY_HISTORY for {len(query_ids)} queries..."
        )

        # Build query
        query_id_list = "', '".join(query_ids)
        sql = f"""
        SELECT
            query_id,
            query_tag,
            warehouse_name,
            warehouse_size,
            start_time,
            end_time,
            total_elapsed_time as total_elapsed_time_ms,
            compilation_time as compilation_time_ms,
            queued_provisioning_time + queued_repair_time + queued_overload_time as queued_time_ms,
            bytes_scanned,
            rows_produced,
            credits_used_cloud_services
        FROM snowflake.account_usage.query_history
        WHERE query_id IN ('{query_id_list}')
        ORDER BY start_time
        """

        cursor = self.conn.cursor(DictCursor)
        cursor.execute(sql)
        results = cursor.fetchall()

        logger.info(f"✅ Retrieved {len(results)} records from ACCOUNT_USAGE")

        if len(results) < len(query_ids):
            missing = len(query_ids) - len(results)
            logger.warning(f"⚠ Warning: {missing} query IDs not found in ACCOUNT_USAGE")
            logger.warning(
                "  This may be normal if less than 45 minutes have passed since execution"
            )

        # Convert to dictionary keyed by query_id
        history_dict = {}
        for row in results:
            # DictCursor returns case-insensitive dict-like objects
            history_dict[row['query_id']] = {
                'compilation_time_ms': row['compilation_time_ms'],
                'queued_time_ms': row['queued_time_ms'],
                'bytes_scanned': row['bytes_scanned'],
                'credits_used_cloud_services': row['credits_used_cloud_services'],
                'total_elapsed_time_ms': row['total_elapsed_time_ms'],
            }

        return history_dict

    def enrich_all(self):
        """
        Main enrichment workflow - enriches all unenriched queries in DuckDB.
        """
        # Get all unenriched queries
        queries = self.get_unenriched_queries()

        if not queries:
            logger.info("\n✅ All results are already enriched, nothing to do!")
            return 0

        query_ids = [q['query_id'] for q in queries]

        # Get ACCOUNT_USAGE data
        history_dict = self.get_query_history_data(query_ids)

        if not history_dict:
            logger.warning("\n⚠ Warning: No data retrieved from ACCOUNT_USAGE")
            logger.warning(
                "Please wait at least 45 minutes after benchmark completion before running enrichment."
            )
            logger.warning(
                "Your queries are in the database but enrichment data is not yet available."
            )
            return 0

        # Update DuckDB with enriched data
        logger.info("\nUpdating DuckDB with enriched data...")
        enriched_count = 0

        for query in queries:
            query_id = query['query_id']

            if query_id not in history_dict:
                logger.warning(f"  Skipping {query_id} - not found in ACCOUNT_USAGE")
                continue

            history = history_dict[query_id]

            try:
                self.storage.update_enrichment_data(
                    query_id=query_id,
                    compilation_time_ms=history.get('compilation_time_ms'),
                    queued_time_ms=history.get('queued_time_ms'),
                    bytes_scanned=history.get('bytes_scanned'),
                    credits_used_compute=None,  # Not available in ACCOUNT_USAGE
                    credits_used_cloud_services=history.get('credits_used_cloud_services'),
                    total_elapsed_time_ms=history.get('total_elapsed_time_ms'),
                )
                enriched_count += 1

            except Exception as e:
                logger.error(f"  Failed to update {query_id}: {e}")
                continue

        logger.info(f"✅ Successfully enriched {enriched_count} queries")

        # Print summary
        self._print_summary(enriched_count, len(queries))

        return enriched_count

    def _print_summary(self, enriched_count: int, total_count: int):
        """Print summary of enrichment results."""
        logger.info("\n" + "=" * 70)
        logger.info("SNOWFLAKE ENRICHMENT SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total unenriched queries found: {total_count}")
        logger.info(f"Successfully enriched: {enriched_count}")
        logger.info(f"Failed/Skipped: {total_count - enriched_count}")

        if enriched_count < total_count:
            logger.warning("\nNOTE: Some queries were not enriched.")
            logger.warning("This may be due to:")
            logger.warning("  - ACCOUNT_USAGE not yet populated (wait 45+ minutes)")
            logger.warning("  - Query IDs not found in ACCOUNT_USAGE")

        logger.info("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enrich all unenriched Snowflake benchmark results with ACCOUNT_USAGE data"
    )
    parser.add_argument(
        "--connection",
        type=str,
        default=SNOWFLAKE_CONNECTION,
        help=f"Snowflake connection name (default: {SNOWFLAKE_CONNECTION})",
    )

    args = parser.parse_args()

    enricher = ResultsEnricher(connection_name=args.connection)

    try:
        enricher.connect()
        enriched_count = enricher.enrich_all()

        if enriched_count > 0:
            logger.info("\n✅ Enrichment complete!")
            logger.info(f"  Enriched {enriched_count} queries in DuckDB")
            return 0
        else:
            logger.info("\n✅ No queries needed enrichment")
            return 0

    except Exception as e:
        logger.error(f"\n❌ Enrichment failed: {e}")
        return 1

    finally:
        enricher.disconnect()


if __name__ == "__main__":
    exit(main())
