#!/usr/bin/env python3
"""
Enrich Benchmark Results with ACCOUNT_USAGE Data

Queries SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY to get detailed metrics
for all queries executed in a benchmark run.

NOTE: Run this script at least 45 minutes after the benchmark completes
to ensure ACCOUNT_USAGE has been populated.
"""

import argparse
import logging
import toml
from pathlib import Path
from typing import List

import pandas as pd
import snowflake.connector
from snowflake.connector import DictCursor
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

from config import (
    SNOWFLAKE_CONNECTION,
    SNOWFLAKE_ROLE,
    SNOWFLAKE_DATABASE,
    SNOWFLAKE_SCHEMA,
)


class ResultsEnricher:
    """Enriches benchmark results with ACCOUNT_USAGE data."""

    def __init__(self, connection_name: str = SNOWFLAKE_CONNECTION):
        """Initialize enricher."""
        self.connection_name = connection_name
        self.conn: snowflake.connector.SnowflakeConnection = None

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

        logger.info("✓ Connected to Snowflake")

    def disconnect(self):
        """Close connection."""
        if self.conn:
            self.conn.close()
            logger.info("✓ Disconnected from Snowflake")

    def load_results(self, results_file: Path) -> pd.DataFrame:
        """Load benchmark results from CSV."""
        logger.info(f"\nLoading results from: {results_file}")
        df = pd.read_csv(results_file)

        # Add enriched columns if they don't exist
        for col in [
            "compilation_time_ms",
            "queued_time_ms",
            "bytes_scanned",
            "credits_used_compute",
            "credits_used_cloud_services",
            "total_elapsed_time_ms",
        ]:
            if col not in df.columns:
                df[col] = None

        logger.info(f"✓ Loaded {len(df)} query results")
        return df

    def get_query_history_data(self, query_ids: List[str]) -> pd.DataFrame:
        """
        Query ACCOUNT_USAGE.QUERY_HISTORY for detailed metrics.

        Args:
            query_ids: List of query IDs to fetch

        Returns:
            DataFrame with query history data
        """
        if not query_ids:
            logger.warning("Warning: No query IDs to fetch")
            return pd.DataFrame()

        logger.info(f"\nQuerying ACCOUNT_USAGE.QUERY_HISTORY for {len(query_ids)} queries...")

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

        logger.info(f"✓ Retrieved {len(results)} records from ACCOUNT_USAGE")

        if len(results) < len(query_ids):
            missing = len(query_ids) - len(results)
            logger.warning(f"⚠ Warning: {missing} query IDs not found in ACCOUNT_USAGE")
            logger.warning(
                "  This may be normal if less than 45 minutes have passed since execution"
            )

        # Convert to DataFrame and normalize column names to lowercase
        df = pd.DataFrame(results)
        df.columns = df.columns.str.lower()
        return df

    def enrich_results(
        self, results_df: pd.DataFrame, history_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Merge benchmark results with ACCOUNT_USAGE data.

        Args:
            results_df: Original benchmark results
            history_df: ACCOUNT_USAGE query history data

        Returns:
            Enriched DataFrame
        """
        logger.info("\nEnriching results with ACCOUNT_USAGE data...")

        # Create a mapping of query_id to enriched data
        history_dict = history_df.set_index("query_id").to_dict("index")

        # Update only rows that need enrichment (where enriched columns are null)
        enriched_count = 0
        for idx, row in results_df.iterrows():
            query_id = row["query_id"]

            # Skip if no query_id or already enriched
            if (
                pd.isna(query_id)
                or query_id == ""
                or pd.notna(row.get("compilation_time_ms"))
            ):
                continue

            # Update with ACCOUNT_USAGE data if available
            if query_id in history_dict:
                history_row = history_dict[query_id]
                results_df.at[idx, "compilation_time_ms"] = history_row.get(
                    "compilation_time_ms"
                )
                results_df.at[idx, "queued_time_ms"] = history_row.get("queued_time_ms")
                results_df.at[idx, "bytes_scanned"] = history_row.get("bytes_scanned")
                results_df.at[idx, "credits_used_cloud_services"] = history_row.get(
                    "credits_used_cloud_services"
                )
                results_df.at[idx, "total_elapsed_time_ms"] = history_row.get(
                    "total_elapsed_time_ms"
                )
                results_df.at[idx, "credits_used_compute"] = None  # Placeholder
                enriched_count += 1

        logger.info(f"✓ Enriched {enriched_count} new results")

        return results_df

    def save_enriched_results(self, enriched_df: pd.DataFrame, output_file: Path):
        """Save enriched results to CSV - overwrites the original file."""
        logger.info(f"\nSaving enriched results to: {output_file}")

        # Use all columns present in the dataframe
        # Use float_format to prevent scientific notation for small numbers
        enriched_df.to_csv(output_file, index=False, float_format='%.10f')

        logger.info(f"✓ Saved enriched results ({len(enriched_df)} rows)")

    def enrich_file(self, results_file: Path) -> Path:
        """
        Main enrichment workflow - enriches rows in-place that don't have enriched data yet.

        Args:
            results_file: Path to benchmark results CSV

        Returns:
            Path to enriched results file (same as input)
        """
        # Load results
        results_df = self.load_results(results_file)

        # Find rows that need enrichment (valid query_id and missing enriched columns)
        needs_enrichment = results_df[
            (results_df["query_id"].notna())
            & (results_df["query_id"] != "")
            & (results_df["compilation_time_ms"].isna())
        ]

        if needs_enrichment.empty:
            logger.info("\n✓ All results are already enriched, nothing to do!")
            return results_file

        query_ids = needs_enrichment["query_id"].tolist()
        logger.info(f"\nFound {len(query_ids)} results that need enrichment")

        # Get ACCOUNT_USAGE data
        history_df = self.get_query_history_data(query_ids)

        if history_df.empty:
            logger.warning("\nWarning: No data retrieved from ACCOUNT_USAGE")
            logger.warning(
                "Please wait at least 45 minutes after benchmark completion before running enrichment."
            )
            logger.warning(
                "The results file has been prepared with enrichment columns but data is not yet available."
            )
            # Still save the file with empty enrichment columns
            self.save_enriched_results(results_df, results_file)
            return results_file

        # Enrich results
        enriched_df = self.enrich_results(results_df, history_df)

        # Save enriched results (in-place)
        self.save_enriched_results(enriched_df, results_file)

        # Print summary statistics
        self._print_summary(enriched_df)

        return results_file

    def _print_summary(self, enriched_df: pd.DataFrame):
        """Print summary statistics of enriched results."""
        logger.info("\n" + "=" * 70)
        logger.info("ENRICHMENT SUMMARY")
        logger.info("=" * 70)

        # Count successful vs failed queries
        successful = len(enriched_df[enriched_df["error_message"] == ""])
        failed = len(enriched_df[enriched_df["error_message"] != ""])

        logger.info(f"Total queries: {len(enriched_df)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")

        if successful > 0:
            logger.info("\nExecution time statistics (successful queries):")
            exec_times = enriched_df[enriched_df["error_message"] == ""][
                "execution_time_sec"
            ]
            logger.info(f"  Mean: {exec_times.mean():.2f}s")
            logger.info(f"  Median: {exec_times.median():.2f}s")
            logger.info(f"  Min: {exec_times.min():.2f}s")
            logger.info(f"  Max: {exec_times.max():.2f}s")

            if "bytes_scanned" in enriched_df.columns:
                total_bytes = enriched_df[enriched_df["error_message"] == ""][
                    "bytes_scanned"
                ].sum()
                logger.info(
                    f"\nTotal bytes scanned: {total_bytes:,.0f} ({total_bytes / 1e9:.2f} GB)"
                )

            if "credits_used_cloud_services" in enriched_df.columns:
                total_credits = enriched_df[enriched_df["error_message"] == ""][
                    "credits_used_cloud_services"
                ].sum()
                logger.info(f"Total cloud services credits: {total_credits:.4f}")

        logger.info("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enrich benchmark results with ACCOUNT_USAGE data"
    )
    parser.add_argument(
        "results_file", type=Path, help="Path to benchmark results CSV file"
    )
    parser.add_argument(
        "--connection",
        type=str,
        default=SNOWFLAKE_CONNECTION,
        help=f"Snowflake connection name (default: {SNOWFLAKE_CONNECTION})",
    )

    args = parser.parse_args()

    if not args.results_file.exists():
        logger.error(f"Error: Results file not found: {args.results_file}")
        return 1

    enricher = ResultsEnricher(connection_name=args.connection)

    try:
        enricher.connect()
        output_file = enricher.enrich_file(args.results_file)

        if output_file:
            logger.info("\n✓ Enrichment complete!")
            logger.info(f"  Output: {output_file}")
            return 0
        else:
            return 1

    finally:
        enricher.disconnect()


if __name__ == "__main__":
    exit(main())
