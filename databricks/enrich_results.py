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
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from databricks import sql

# Initialize centralized logging
sys.path.insert(0, str(Path(__file__).parent.parent))
from common.logging_config import get_logger
from common.storage import BenchmarkStorage

logger = get_logger(__name__)

from config import (
    DATABRICKS_HOST,
    DATABRICKS_TOKEN,
    CATALOG,
    DUCKDB_PATH,
)


class DatabricksResultsEnricher:
    """Enriches Databricks benchmark results with system table data."""

    def __init__(self):
        """Initialize enricher."""
        self.storage = BenchmarkStorage(DUCKDB_PATH)
        self.conn: Optional[sql.client.Connection] = None

    def connect(self):
        """Establish connection to Databricks for querying system tables."""
        logger.info(f"Connecting to Databricks to query system tables...")

        try:
            # Clean hostname (remove https:// prefix if present)
            hostname = DATABRICKS_HOST.replace("https://", "").replace("http://", "")

            # For system tables, we can connect without specifying a warehouse
            # We'll use SQL Execution API directly
            self.conn = sql.connect(
                server_hostname=hostname,
                http_path="/sql/1.0/warehouses/system",  # Use system warehouse for system tables
                access_token=DATABRICKS_TOKEN,
            )

            # Set catalog to system for querying system tables
            cursor = self.conn.cursor()
            cursor.execute("USE CATALOG system")
            cursor.close()

            logger.info("✅ Connected to Databricks (system catalog)")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Databricks: {e}")
            logger.info("Note: System tables require appropriate permissions")
            raise

    def disconnect(self):
        """Close connection."""
        if self.conn:
            self.conn.close()
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

        # Build query - system.query.history schema
        # Reference: https://docs.databricks.com/en/admin/system-tables/query-history.html
        statement_id_list = "', '".join(statement_ids)

        try:
            sql_query = f"""
            SELECT
                statement_id,
                executed_as_user_name,
                start_time,
                end_time,
                total_task_duration_ms,
                compilation_time_ms,
                execution_time_ms,
                read_bytes,
                read_rows,
                written_bytes,
                produced_rows,
                error_message
            FROM system.query.history
            WHERE statement_id IN ('{statement_id_list}')
            AND start_time >= '{start_buffer.isoformat()}'
            AND start_time <= '{end_buffer.isoformat()}'
            ORDER BY start_time
            """

            cursor = self.conn.cursor()
            cursor.execute(sql_query)
            results = cursor.fetchall()
            cursor.close()

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
                    'compilation_time_ms': row[5],
                    'execution_time_ms': row[6],
                    'read_bytes': row[7],
                    'read_rows': row[8],
                    'written_bytes': row[9],
                    'produced_rows': row[10],
                    'error_message': row[11],
                }

            return history_dict

        except Exception as e:
            logger.error(f"❌ Failed to query system.query.history: {e}")
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

            cursor = self.conn.cursor()
            cursor.execute(sql_query)
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

            execution_ms = query_history[statement_id].get('execution_time_ms', 0)
            if not execution_ms:
                logger.warning(f"  Query {statement_id} has no execution time, skipping cost calculation")
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
                    compilation_time_ms=history.get('compilation_time_ms'),
                    queued_time_ms=None,  # Not directly available in query history
                    bytes_scanned=history.get('read_bytes'),
                    credits_used_compute=cost,  # Approximate DBU cost
                    credits_used_cloud_services=None,  # Not applicable for Databricks
                    total_elapsed_time_ms=history.get('execution_time_ms'),
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

    args = parser.parse_args()

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
