#!/usr/bin/env python3
"""
Enrich Benchmark Results with ACCOUNT_USAGE Data

Queries SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY to get detailed metrics
for all queries executed in a benchmark run.

NOTE: Run this script at least 45 minutes after the benchmark completes
to ensure ACCOUNT_USAGE has been populated.
"""

import csv
import argparse
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import snowflake.connector
from snowflake.connector import DictCursor

from config import (
    SNOWFLAKE_CONNECTION,
    SNOWFLAKE_ROLE,
    ENRICHED_CSV_COLUMNS,
)


class ResultsEnricher:
    """Enriches benchmark results with ACCOUNT_USAGE data."""

    def __init__(self, connection_name: str = SNOWFLAKE_CONNECTION):
        """Initialize enricher."""
        self.connection_name = connection_name
        self.conn: snowflake.connector.SnowflakeConnection = None

    def connect(self):
        """Establish connection to Snowflake."""
        print(f"Connecting to Snowflake using connection: {self.connection_name}")
        self.conn = snowflake.connector.connect(
            connection_name=self.connection_name,
            role=SNOWFLAKE_ROLE,
        )
        print("✓ Connected to Snowflake")

    def disconnect(self):
        """Close connection."""
        if self.conn:
            self.conn.close()
            print("✓ Disconnected from Snowflake")

    def load_results(self, results_file: Path) -> pd.DataFrame:
        """Load benchmark results from CSV."""
        print(f"\nLoading results from: {results_file}")
        df = pd.read_csv(results_file)
        print(f"✓ Loaded {len(df)} query results")
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
            print("Warning: No query IDs to fetch")
            return pd.DataFrame()

        print(f"\nQuerying ACCOUNT_USAGE.QUERY_HISTORY for {len(query_ids)} queries...")

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

        print(f"✓ Retrieved {len(results)} records from ACCOUNT_USAGE")

        if len(results) < len(query_ids):
            missing = len(query_ids) - len(results)
            print(f"⚠ Warning: {missing} query IDs not found in ACCOUNT_USAGE")
            print("  This may be normal if less than 45 minutes have passed since execution")

        return pd.DataFrame(results)

    def enrich_results(self, results_df: pd.DataFrame, history_df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge benchmark results with ACCOUNT_USAGE data.

        Args:
            results_df: Original benchmark results
            history_df: ACCOUNT_USAGE query history data

        Returns:
            Enriched DataFrame
        """
        print("\nEnriching results with ACCOUNT_USAGE data...")

        # Merge on query_id
        enriched = results_df.merge(
            history_df,
            on='query_id',
            how='left',
            suffixes=('', '_account')
        )

        # Add columns that are only in history but not in original results
        for col in ['compilation_time_ms', 'queued_time_ms', 'bytes_scanned',
                    'credits_used_cloud_services', 'total_elapsed_time_ms']:
            if col not in enriched.columns and col in history_df.columns:
                enriched[col] = history_df[col]

        # Calculate compute credits (estimate, as it's not directly in query_history)
        # Use warehouse_metering_history for accurate credit tracking
        if 'total_elapsed_time_ms' in enriched.columns:
            enriched['credits_used_compute'] = None  # Placeholder - needs warehouse_metering_history

        print(f"✓ Enriched {len(enriched)} results")

        return enriched

    def save_enriched_results(self, enriched_df: pd.DataFrame, output_file: Path):
        """Save enriched results to CSV."""
        print(f"\nSaving enriched results to: {output_file}")

        # Select only columns defined in ENRICHED_CSV_COLUMNS that exist
        available_columns = [col for col in ENRICHED_CSV_COLUMNS if col in enriched_df.columns]
        enriched_df[available_columns].to_csv(output_file, index=False)

        print(f"✓ Saved enriched results ({len(enriched_df)} rows)")

    def enrich_file(self, results_file: Path) -> Path:
        """
        Main enrichment workflow.

        Args:
            results_file: Path to original benchmark results CSV

        Returns:
            Path to enriched results file
        """
        # Load original results
        results_df = self.load_results(results_file)

        # Filter out rows with no query_id (errors)
        valid_results = results_df[results_df['query_id'].notna() & (results_df['query_id'] != '')]
        query_ids = valid_results['query_id'].tolist()

        if not query_ids:
            print("Error: No valid query IDs found in results file")
            return None

        # Get ACCOUNT_USAGE data
        history_df = self.get_query_history_data(query_ids)

        if history_df.empty:
            print("\nError: No data retrieved from ACCOUNT_USAGE")
            print("Please wait at least 45 minutes after benchmark completion before running enrichment.")
            return None

        # Enrich results
        enriched_df = self.enrich_results(results_df, history_df)

        # Save enriched results
        output_file = results_file.parent / f"{results_file.stem}_enriched.csv"
        self.save_enriched_results(enriched_df, output_file)

        # Print summary statistics
        self._print_summary(enriched_df)

        return output_file

    def _print_summary(self, enriched_df: pd.DataFrame):
        """Print summary statistics of enriched results."""
        print("\n" + "=" * 70)
        print("ENRICHMENT SUMMARY")
        print("=" * 70)

        # Count successful vs failed queries
        successful = len(enriched_df[enriched_df['error_message'] == ''])
        failed = len(enriched_df[enriched_df['error_message'] != ''])

        print(f"Total queries: {len(enriched_df)}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")

        if successful > 0:
            print(f"\nExecution time statistics (successful queries):")
            exec_times = enriched_df[enriched_df['error_message'] == '']['execution_time_sec']
            print(f"  Mean: {exec_times.mean():.2f}s")
            print(f"  Median: {exec_times.median():.2f}s")
            print(f"  Min: {exec_times.min():.2f}s")
            print(f"  Max: {exec_times.max():.2f}s")

            if 'bytes_scanned' in enriched_df.columns:
                total_bytes = enriched_df[enriched_df['error_message'] == '']['bytes_scanned'].sum()
                print(f"\nTotal bytes scanned: {total_bytes:,.0f} ({total_bytes / 1e9:.2f} GB)")

            if 'credits_used_cloud_services' in enriched_df.columns:
                total_credits = enriched_df[enriched_df['error_message'] == '']['credits_used_cloud_services'].sum()
                print(f"Total cloud services credits: {total_credits:.4f}")

        print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Enrich benchmark results with ACCOUNT_USAGE data'
    )
    parser.add_argument(
        'results_file',
        type=Path,
        help='Path to benchmark results CSV file'
    )
    parser.add_argument(
        '--connection',
        type=str,
        default=SNOWFLAKE_CONNECTION,
        help=f'Snowflake connection name (default: {SNOWFLAKE_CONNECTION})'
    )

    args = parser.parse_args()

    if not args.results_file.exists():
        print(f"Error: Results file not found: {args.results_file}")
        return 1

    enricher = ResultsEnricher(connection_name=args.connection)

    try:
        enricher.connect()
        output_file = enricher.enrich_file(args.results_file)

        if output_file:
            print(f"\n✓ Enrichment complete!")
            print(f"  Output: {output_file}")
            return 0
        else:
            return 1

    finally:
        enricher.disconnect()


if __name__ == '__main__':
    exit(main())
