#!/usr/bin/env python3
"""
Enrich Benchmark Results with ACCOUNT_USAGE Data

For every unenriched query in DuckDB, pulls two things from Snowflake:

  1. Per-query metrics from ACCOUNT_USAGE.QUERY_HISTORY (compilation/queued
     times, bytes scanned, cloud services credits, total elapsed time).
  2. Compute credits attributed to each query — allocated proportionally
     by total_elapsed_time from ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY,
     scoped to the warehouse the query ran on.

Per-query compute credits are NOT directly available in QUERY_HISTORY for
either gen1 standard or adaptive warehouses. WAREHOUSE_METERING_HISTORY is
the authoritative compute-cost source. We attribute proportionally by elapsed
time, which is the standard Snowflake chargeback pattern.

Because each benchmark variant (gen1 vs adaptive, each QTM, each size) runs
on its OWN uniquely-named warehouse, the metering rows attribute cleanly to
the variant without smearing.

NOTE: Run this at least ~90 minutes after the benchmark completes. ACCOUNT_USAGE
latency is documented as ~45 min but can stretch longer; adaptive billing may
take longer to settle than gen1.
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
    ADMIN_WAREHOUSE,
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
        """Load connection config from ~/.snowflake/connections.toml or config.toml."""
        snowflake_dir = Path.home() / ".snowflake"
        connections_file = snowflake_dir / "connections.toml"
        config_file = snowflake_dir / "config.toml"

        if connections_file.exists():
            config = toml.load(connections_file)
            if connection_name in config:
                return config[connection_name]

        if config_file.exists():
            config = toml.load(config_file)
            nested = config.get("connections", {})
            if connection_name in nested:
                return nested[connection_name]

        if not connections_file.exists() and not config_file.exists():
            raise FileNotFoundError(
                f"Snowflake config not found at {connections_file} or {config_file}"
            )
        raise ValueError(
            f"Connection '{connection_name}' not found in connections.toml or config.toml"
        )

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
        cursor.execute(f"USE WAREHOUSE {ADMIN_WAREHOUSE}")
        cursor.close()

        logger.info("✅ Connected to Snowflake")

    def disconnect(self):
        """Close connection."""
        if self.conn:
            self.conn.close()
            logger.info("✅ Disconnected from Snowflake")

    def get_unenriched_queries(self) -> List[Dict[str, Any]]:
        """Get all unenriched queries from DuckDB, including warehouse_name so
        we can allocate compute credits per warehouse later."""
        logger.info("\nFetching unenriched queries from DuckDB...")

        results = self.storage.query("""
            SELECT query_id, run_id, query_num, run_num, warehouse_name
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
                'warehouse_name': row[4],
            })

        logger.info(f"✅ Found {len(queries)} unenriched queries")
        return queries

    def get_warehouse_metering_credits(
        self, warehouse_names: List[str]
    ) -> Dict[str, float]:
        """
        Fetch total compute credits per warehouse from WAREHOUSE_METERING_HISTORY.

        WAREHOUSE_METERING_HISTORY reports actual billed compute credits
        (credits_used_compute) per warehouse per hour. We sum across all hour
        buckets for the warehouse to get its total billed compute, then later
        allocate to queries proportionally by total_elapsed_time.

        For adaptive warehouses this view is still authoritative; per-query
        compute credit columns are not exposed in QUERY_HISTORY.
        """
        if not warehouse_names:
            return {}

        names_list = "', '".join(warehouse_names)
        sql = f"""
        SELECT warehouse_name,
               SUM(credits_used_compute) AS total_compute_credits
        FROM snowflake.account_usage.warehouse_metering_history
        WHERE warehouse_name IN ('{names_list}')
        GROUP BY warehouse_name
        """
        logger.info(
            f"\nQuerying WAREHOUSE_METERING_HISTORY for {len(warehouse_names)} warehouses..."
        )
        cursor = self.conn.cursor(DictCursor)
        cursor.execute(sql)
        results = cursor.fetchall()
        credits_by_wh = {
            row['WAREHOUSE_NAME']: float(row['TOTAL_COMPUTE_CREDITS'] or 0.0)
            for row in results
        }
        logger.info(f"✅ Retrieved metering rows for {len(credits_by_wh)} warehouses")
        missing = set(warehouse_names) - set(credits_by_wh)
        if missing:
            logger.warning(
                f"⚠ {len(missing)} warehouses have no metering rows yet: {sorted(missing)[:3]}..."
            )
        return credits_by_wh

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
            # DictCursor returns uppercase column names
            history_dict[row['QUERY_ID']] = {
                'compilation_time_ms': row['COMPILATION_TIME_MS'],
                'queued_time_ms': row['QUEUED_TIME_MS'],
                'bytes_scanned': row['BYTES_SCANNED'],
                'credits_used_cloud_services': row['CREDITS_USED_CLOUD_SERVICES'],
                'total_elapsed_time_ms': row['TOTAL_ELAPSED_TIME_MS'],
            }

        return history_dict

    def enrich_all(self):
        """Main enrichment workflow — enriches all unenriched queries in DuckDB."""
        queries = self.get_unenriched_queries()

        if not queries:
            logger.info("\n✅ All results are already enriched, nothing to do!")
            return 0

        query_ids = [q['query_id'] for q in queries]
        warehouse_names = sorted({q['warehouse_name'] for q in queries if q.get('warehouse_name')})

        history_dict = self.get_query_history_data(query_ids)
        wh_credits = self.get_warehouse_metering_credits(warehouse_names)

        if not history_dict:
            logger.warning("\n⚠ Warning: No data retrieved from ACCOUNT_USAGE")
            logger.warning(
                "Please wait at least 90 minutes after benchmark completion."
            )
            return 0

        # Allocate compute credits to queries by proportional elapsed time
        # per warehouse. Build elapsed-time totals first, then divide.
        elapsed_by_wh: Dict[str, float] = {}
        for q in queries:
            wh = q.get('warehouse_name')
            hist = history_dict.get(q['query_id'])
            if not wh or not hist:
                continue
            elapsed_by_wh[wh] = elapsed_by_wh.get(wh, 0.0) + float(
                hist.get('total_elapsed_time_ms') or 0.0
            )

        logger.info("\nUpdating DuckDB with enriched data...")
        enriched_count = 0

        for query in queries:
            query_id = query['query_id']
            wh = query.get('warehouse_name')

            if query_id not in history_dict:
                logger.warning(f"  Skipping {query_id} - not found in ACCOUNT_USAGE")
                continue

            history = history_dict[query_id]

            # Proportional compute-credit allocation: this query's share of
            # the warehouse's elapsed time, multiplied by the warehouse's
            # total billed compute credits.
            credits_compute = None
            wh_total_credits = wh_credits.get(wh)
            wh_total_elapsed = elapsed_by_wh.get(wh, 0.0)
            this_elapsed = float(history.get('total_elapsed_time_ms') or 0.0)
            if wh_total_credits is not None and wh_total_elapsed > 0:
                credits_compute = wh_total_credits * (this_elapsed / wh_total_elapsed)

            try:
                self.storage.update_enrichment_data(
                    query_id=query_id,
                    compilation_time_ms=history.get('compilation_time_ms'),
                    queued_time_ms=history.get('queued_time_ms'),
                    bytes_scanned=history.get('bytes_scanned'),
                    credits_used_compute=credits_compute,
                    credits_used_cloud_services=history.get('credits_used_cloud_services'),
                    total_elapsed_time_ms=history.get('total_elapsed_time_ms'),
                )
                enriched_count += 1

            except Exception as e:
                logger.error(f"  Failed to update {query_id}: {e}")
                continue

        logger.info(f"✅ Successfully enriched {enriched_count} queries")
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
            logger.warning("  - ACCOUNT_USAGE not yet populated (wait 90+ minutes)")
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
