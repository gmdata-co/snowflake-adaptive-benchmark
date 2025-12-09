#!/usr/bin/env python3
"""
Enrich Databricks Benchmark Results with System Table Data

Queries system.query.history and system.billing.usage to get detailed metrics
for all queries executed in a benchmark run.

NOTE: Run this script at least 1-2 hours after the benchmark completes
to ensure system tables have been populated. Unlike Snowflake's documented
45-minute SLA, Databricks system table latency is variable and undocumented.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Initialize centralized logging
sys.path.insert(0, str(Path(__file__).parent.parent))
from common.logging_config import get_logger
from common.storage import BenchmarkStorage
from common.connections.databricks_connection import DatabricksConnection
from config import (
    DATABRICKS_HOST,
    DATABRICKS_TOKEN,
    CATALOG,
    DUCKDB_PATH,
    WAREHOUSES,
)

logger = get_logger(__name__)


class DatabricksResultsEnricher:
    """Enriches Databricks benchmark results with system table data."""

    def __init__(self):
        """Initialize enricher."""
        self.storage = BenchmarkStorage(DUCKDB_PATH)
        self.db_conn: Optional[DatabricksConnection] = None

    def connect(self):
        """Establish connection to Databricks for querying system tables."""
        logger.info("Connecting to Databricks to query system tables...")

        # Use admin warehouse to query system tables (system tables are accessible from any warehouse)
        warehouse_id = WAREHOUSES.get("admin")
        if not warehouse_id:
            raise ValueError("Admin warehouse not configured in .env file (DATABRICKS_ADMIN_WAREHOUSE)")

        logger.info(f"  Using warehouse: {warehouse_id}")
        logger.info(f"  Host: {DATABRICKS_HOST}")

        try:
            # Use the common DatabricksConnection class
            # Note: We use CATALOG from config initially, then switch to 'system' catalog
            logger.info("  Establishing connection to warehouse...")
            self.db_conn = DatabricksConnection(
                host=DATABRICKS_HOST,
                token=DATABRICKS_TOKEN,
                warehouse_id=warehouse_id,
                catalog=CATALOG,  # Initial catalog (will switch to system below)
                schema="information_schema",  # Dummy schema (not used for system tables)
            )

            self.db_conn.connect()
            logger.info("  ✅ Warehouse connection established")

            # Switch to system catalog for querying system tables
            logger.info("  Switching to system catalog...")
            cursor = self.db_conn.get_cursor()
            cursor.execute("USE CATALOG system")
            cursor.close()
            logger.info("  ✅ Switched to system catalog")

            logger.info("✅ Connected to Databricks - ready to query system tables")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Databricks: {e}")
            logger.info("Note: System tables require appropriate permissions")
            raise

    def disconnect(self):
        """Close connection."""
        if self.db_conn:
            self.db_conn.disconnect()
            logger.info("✅ Disconnected from Databricks")

    def get_run_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about all unenriched queries from DuckDB.

        Returns:
            Dictionary with run metadata (timestamps, warehouse_ids, etc.)
        """
        logger.info("\nFetching unenriched queries from DuckDB...")

        # Get all unenriched queries
        results = self.storage.query("""
            SELECT
                query_id,
                warehouse_name,
                timestamp,
                query_num,
                run_num,
                run_id
            FROM databricks_results
            WHERE query_id IS NOT NULL
            AND query_id != ''
            AND compilation_time_ms IS NULL
            ORDER BY timestamp
        """)

        if not results:
            logger.warning("No unenriched queries found")
            return {}

        queries = []
        for row in results:
            queries.append({
                'query_id': row[0],
                'warehouse_id': row[1],
                'timestamp': row[2],
                'query_num': row[3],
                'run_num': row[4],
                'run_id': row[5],
            })

        # Get time range
        min_timestamp = min(q['timestamp'] for q in queries)
        max_timestamp = max(q['timestamp'] for q in queries)

        logger.info(f"✅ Found {len(queries)} queries to enrich")
        logger.info(f"  Time range: {min_timestamp} to {max_timestamp}")

        return {
            'queries': queries,
            'min_timestamp': min_timestamp,
            'max_timestamp': max_timestamp,
            'warehouse_ids': list(set(q['warehouse_id'] for q in queries)),
        }

    def get_query_history_data(self, statement_ids: List[str], start_time: datetime, end_time: datetime) -> Dict[str, Dict]:
        """
        Query system.query.history for detailed query metrics.

        Args:
            statement_ids: List of Databricks statement IDs to fetch
            start_time: Start of time range to query
            end_time: End of time range to query

        Returns:
            Dictionary mapping statement_id to metrics
        """
        if not statement_ids:
            logger.warning("No statement IDs to fetch")
            return {}

        logger.info(f"\nQuerying system.query.history for {len(statement_ids)} queries...")

        # Add buffer to time range (system tables may have slight time drift)
        start_buffer = start_time - timedelta(minutes=5)
        end_buffer = end_time + timedelta(minutes=5)

        logger.info(f"  Time range: {start_buffer.isoformat()} to {end_buffer.isoformat()}")
        logger.info(f"  Sample statement IDs: {statement_ids[:3]}")

        # Build query - system.query.history schema
        # Reference: https://docs.databricks.com/en/admin/system-tables/query-history.html
        statement_id_list = "', '".join(statement_ids)

        try:
            sql_query = f"""
            SELECT
                statement_id,
                executed_as_user_id,
                start_time,
                end_time,
                total_task_duration_ms,
                compilation_duration_ms,
                execution_duration_ms,
                read_bytes,
                read_rows,
                written_bytes,
                rows_produced,
                error_message
            FROM system.query.history
            WHERE statement_id IN ('{statement_id_list}')
            AND start_time >= '{start_buffer.isoformat()}'
            AND start_time <= '{end_buffer.isoformat()}'
            ORDER BY start_time
            """

            # First, do a sanity check - can we query system.query.history at all?
            logger.info("  Running sanity check: querying recent queries from system.query.history...")
            # Skip sanity check for now - the Databricks connector has a bug with NULL values
            # We'll just try the main query and see if it works
            logger.info("  (Skipping COUNT check due to Databricks connector bug with NULL values)")

            logger.info("  Executing main query against system.query.history...")
            logger.info(f"  Full query (first 500 chars):\n{sql_query[:500]}")

            cursor = self.db_conn.get_cursor()
            cursor.execute(sql_query)

            logger.info("  Fetching results (using Arrow to avoid pandas NULL bug)...")
            # Use fetchall_arrow() to get Arrow table, then convert to Python dicts
            # This avoids the pandas NULL conversion bug
            arrow_table = cursor.fetchall_arrow()
            results = arrow_table.to_pylist() if arrow_table else []
            cursor.close()

            # Convert list of dicts back to list of tuples to match expected format
            if results:
                results = [tuple(row.values()) for row in results]

            logger.info(f"✅ Retrieved {len(results)} records from system.query.history")

            if len(results) < len(statement_ids):
                missing = len(statement_ids) - len(results)
                logger.warning(f"⚠ Warning: {missing} statement IDs not found in system.query.history")
                logger.warning("  This may be normal if system tables haven't been populated yet")
                logger.warning("  Recommendation: Wait 1-2 hours after benchmark completion")

            # Convert to dictionary keyed by statement_id
            history_dict = {}
            for row in results:
                statement_id = row[0]
                history_dict[statement_id] = {
                    'statement_id': row[0],
                    'user': row[1],
                    'start_time': row[2],
                    'end_time': row[3],
                    'total_task_duration_ms': row[4],
                    'compilation_duration_ms': row[5],  # Databricks uses 'duration' not 'time'
                    'execution_duration_ms': row[6],    # Databricks uses 'duration' not 'time'
                    'read_bytes': row[7],
                    'read_rows': row[8],
                    'written_bytes': row[9],
                    'rows_produced': row[10],
                    'error_message': row[11],
                }

            return history_dict

        except Exception as e:
            import traceback
            logger.error(f"❌ Failed to query system.query.history: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            logger.warning("Ensure you have SELECT permissions on system.query.history")
            return {}

    def get_billing_data(self, warehouse_ids: List[str], start_time: datetime, end_time: datetime) -> Dict[str, List[Dict]]:
        """
        Query system.billing.usage for DBU consumption data.

        Args:
            warehouse_ids: List of warehouse IDs used in the benchmark
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Dictionary mapping warehouse_id to list of hourly usage records
        """
        if not warehouse_ids:
            logger.warning("No warehouse IDs provided")
            return {}

        logger.info(f"\nQuerying system.billing.usage for {len(warehouse_ids)} warehouses...")

        # Add buffer to time range
        start_buffer = start_time - timedelta(hours=1)
        end_buffer = end_time + timedelta(hours=1)

        logger.info(f"  Date range: {start_buffer.date()} to {end_buffer.date()}")
        logger.info(f"  Warehouses: {warehouse_ids}")

        # Build query - system.billing.usage schema
        # Reference: https://docs.databricks.com/en/admin/system-tables/billing.html
        warehouse_id_list = "', '".join(warehouse_ids)

        try:
            sql_query = f"""
            SELECT
                usage_metadata.warehouse_id,
                usage_date,
                usage_start_time,
                usage_end_time,
                usage_quantity,
                usage_unit
            FROM system.billing.usage
            WHERE usage_metadata.warehouse_id IN ('{warehouse_id_list}')
            AND usage_date >= DATE('{start_buffer.date()}')
            AND usage_date <= DATE('{end_buffer.date()}')
            AND usage_unit = 'DBU'
            ORDER BY usage_start_time
            """

            logger.info("  Executing query against system.billing.usage...")
            logger.debug(f"  Query: {sql_query[:200]}...")

            cursor = self.db_conn.get_cursor()
            cursor.execute(sql_query)

            logger.info("  Fetching billing results...")
            results = cursor.fetchall()
            cursor.close()

            logger.info(f"✅ Retrieved {len(results)} billing records from system.billing.usage")

            # Group by warehouse_id
            billing_dict = {}
            for row in results:
                warehouse_id = row[0]
                if warehouse_id not in billing_dict:
                    billing_dict[warehouse_id] = []

                billing_dict[warehouse_id].append({
                    'warehouse_id': row[0],
                    'usage_date': row[1],
                    'usage_start_time': row[2],
                    'usage_end_time': row[3],
                    'usage_quantity': row[4],  # DBUs consumed
                    'usage_unit': row[5],
                })

            return billing_dict

        except Exception as e:
            logger.error(f"❌ Failed to query system.billing.usage: {e}")
            logger.warning("Ensure you have SELECT permissions on system.billing.usage")
            logger.warning("Note: Billing data may have significant latency (hours to days)")
            return {}

    def calculate_query_costs(
        self,
        queries: List[Dict],
        query_history: Dict[str, Dict],
        billing_data: Dict[str, List[Dict]]
    ) -> Dict[str, float]:
        """
        Calculate approximate DBU cost per query by distributing warehouse costs proportionally.

        Args:
            queries: List of query metadata from DuckDB
            query_history: Query execution details from system.query.history
            billing_data: Warehouse billing data from system.billing.usage

        Returns:
            Dictionary mapping statement_id to estimated DBU cost
        """
        logger.info("\nCalculating proportional query costs...")

        query_costs = {}

        for query in queries:
            statement_id = query['query_id']
            warehouse_id = query['warehouse_id']
            query_time = query['timestamp']

            # Get execution time from query history (more accurate than client timing)
            if statement_id not in query_history:
                logger.warning(f"  Query {statement_id} not found in query history, skipping cost calculation")
                query_costs[statement_id] = None
                continue

            execution_ms = query_history[statement_id].get('execution_duration_ms', 0)
            if not execution_ms:
                logger.warning(f"  Query {statement_id} has no execution duration, skipping cost calculation")
                query_costs[statement_id] = None
                continue

            # Find matching billing period
            if warehouse_id not in billing_data:
                logger.warning(f"  No billing data for warehouse {warehouse_id}, skipping cost calculation")
                query_costs[statement_id] = None
                continue

            # Find the billing period that contains this query
            matching_period = None
            for period in billing_data[warehouse_id]:
                if period['usage_start_time'] <= query_time <= period['usage_end_time']:
                    matching_period = period
                    break

            if not matching_period:
                # Try to find nearest period
                logger.warning(f"  No exact billing period match for query at {query_time}, using nearest period")
                # This is expected - billing is often aggregated by hour
                # We'll use the first period for now as an approximation
                if billing_data[warehouse_id]:
                    matching_period = billing_data[warehouse_id][0]
                else:
                    query_costs[statement_id] = None
                    continue

            # Calculate proportional cost
            # Cost per query = (query_duration_ms / period_duration_ms) * period_dbu_cost
            period_start = matching_period['usage_start_time']
            period_end = matching_period['usage_end_time']
            period_duration_ms = (period_end - period_start).total_seconds() * 1000
            period_dbu = matching_period['usage_quantity']

            if period_duration_ms > 0:
                proportional_dbu = (execution_ms / period_duration_ms) * period_dbu
                query_costs[statement_id] = proportional_dbu
            else:
                query_costs[statement_id] = None

        logger.info(f"✅ Calculated costs for {sum(1 for c in query_costs.values() if c is not None)} queries")

        return query_costs

    def enrich_results(self, metadata: Dict[str, Any]):
        """
        Main enrichment workflow - update DuckDB with system table data.

        Args:
            metadata: Run metadata from get_run_metadata()
        """
        queries = metadata.get('queries', [])
        if not queries:
            logger.warning("No queries to enrich")
            return

        statement_ids = [q['query_id'] for q in queries]
        start_time = metadata['min_timestamp']
        end_time = metadata['max_timestamp']
        warehouse_ids = metadata['warehouse_ids']

        # Fetch query history data
        query_history = self.get_query_history_data(statement_ids, start_time, end_time)

        # Fetch billing data
        billing_data = self.get_billing_data(warehouse_ids, start_time, end_time)

        # Calculate query costs
        query_costs = self.calculate_query_costs(queries, query_history, billing_data)

        # Update DuckDB with enriched data
        logger.info("\nUpdating DuckDB with enriched data...")
        enriched_count = 0

        for query in queries:
            statement_id = query['query_id']

            if statement_id not in query_history:
                logger.warning(f"  Skipping {statement_id} - not found in query history")
                continue

            history = query_history[statement_id]
            cost = query_costs.get(statement_id)

            try:
                self.storage.update_databricks_enrichment_data(
                    query_id=statement_id,
                    compilation_time_ms=history.get('compilation_duration_ms'),  # Databricks uses 'duration'
                    queued_time_ms=None,  # Not directly available in query history
                    bytes_scanned=history.get('read_bytes'),
                    credits_used_compute=cost,  # Approximate DBU cost
                    credits_used_cloud_services=None,  # Not applicable for Databricks
                    total_elapsed_time_ms=history.get('execution_duration_ms'),  # Databricks uses 'duration'
                    rows_produced=history.get('rows_produced'),  # Fetch row count from system table
                )
                enriched_count += 1

            except Exception as e:
                logger.error(f"  Failed to update {statement_id}: {e}")
                continue

        logger.info(f"✅ Successfully enriched {enriched_count} queries")

        # Print summary
        self._print_summary(enriched_count, len(queries))

    def _print_summary(self, enriched_count: int, total_count: int):
        """Print summary of enrichment results."""
        logger.info("\n" + "=" * 70)
        logger.info("DATABRICKS ENRICHMENT SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total unenriched queries found: {total_count}")
        logger.info(f"Successfully enriched: {enriched_count}")
        logger.info(f"Failed/Skipped: {total_count - enriched_count}")

        if enriched_count < total_count:
            logger.warning("\nNOTE: Some queries were not enriched.")
            logger.warning("This may be due to:")
            logger.warning("  - System tables not yet populated (wait longer)")
            logger.warning("  - Missing permissions on system.query.history or system.billing.usage")
            logger.warning("  - Statement IDs not found in system tables")

        logger.info("\nNOTE: DBU costs are APPROXIMATIONS based on proportional distribution")
        logger.info("of warehouse-hour costs across queries. This differs from Snowflake's")
        logger.info("exact per-query credit tracking.")
        logger.info("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enrich all unenriched Databricks benchmark results with system table data"
    )

    parser.parse_args()

    enricher = DatabricksResultsEnricher()

    try:
        # Get run metadata from DuckDB
        metadata = enricher.get_run_metadata()

        if not metadata:
            logger.info("✅ No queries need enrichment")
            return 0

        # Connect to Databricks
        enricher.connect()

        # Enrich results
        enricher.enrich_results(metadata)

        logger.info("\n✅ Enrichment complete!")
        return 0

    except Exception as e:
        logger.error(f"\n❌ Enrichment failed: {e}")
        return 1

    finally:
        enricher.disconnect()


if __name__ == "__main__":
    exit(main())
