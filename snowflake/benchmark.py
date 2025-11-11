#!/usr/bin/env python3
"""
Snowflake TPC-H Benchmark Runner

Executes TPC-H queries against Snowflake and logs performance metrics.
"""

import csv
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import argparse
import toml

import snowflake.connector
from snowflake.connector import DictCursor
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from config import (
    SNOWFLAKE_CONNECTION,
    SNOWFLAKE_ROLE,
    SNOWFLAKE_DATABASE,
    SNOWFLAKE_SCHEMA,
    WAREHOUSES,
    NUM_RUNS,
    NUM_QUERIES,
    COLD_START_DELAY,
    APP_NAME,
    QUERIES_DIR,
    RESULTS_DIR,
    CSV_COLUMNS,
)


class SnowflakeBenchmark:
    """Manages Snowflake TPC-H benchmark execution."""

    def __init__(self, connection_name: str = SNOWFLAKE_CONNECTION):
        """Initialize benchmark runner."""
        self.connection_name = connection_name
        self.conn: Optional[snowflake.connector.SnowflakeConnection] = None
        self.run_id = str(uuid.uuid4())
        self.csv_file = RESULTS_DIR / "benchmark_results.csv"
        self.csv_writer: Optional[csv.DictWriter] = None
        self.csv_handle = None

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
        print(f"Connecting to Snowflake using connection: {self.connection_name}")

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

        # Disable result caching to ensure accurate benchmarking
        self._execute("ALTER SESSION SET USE_CACHED_RESULT = FALSE")
        print("✓ Connected to Snowflake")
        print(f"✓ Using role: {SNOWFLAKE_ROLE}")
        print(f"✓ Database: {SNOWFLAKE_DATABASE}")

    def disconnect(self):
        """Close Snowflake connection."""
        if self.conn:
            self.conn.close()
            print("✓ Disconnected from Snowflake")

    def _execute(
        self, sql: str, async_exec: bool = False
    ) -> snowflake.connector.cursor.SnowflakeCursor:
        """
        Execute SQL statement.

        Args:
            sql: SQL statement to execute
            async_exec: If True, execute asynchronously

        Returns:
            Cursor object
        """
        cursor = self.conn.cursor()
        if async_exec:
            cursor.execute_async(sql)
        else:
            cursor.execute(sql)
        return cursor

    def switch_warehouse(self, warehouse_name: str):
        """Switch to a different warehouse."""
        print(f"\nSwitching to warehouse: {warehouse_name}")
        self._execute(f"USE WAREHOUSE {warehouse_name}")

    def load_query(self, query_num: int) -> str:
        """Load TPC-H query from file."""
        query_file = QUERIES_DIR / f"q{query_num:02d}.sql"
        if not query_file.exists():
            raise FileNotFoundError(f"Query file not found: {query_file}")

        with open(query_file, "r") as f:
            return f.read().strip()

    def set_query_tag(self, query_tag: Dict[str, Any]):
        """
        Set the query tag for the next query.

        Args:
            query_tag: Dictionary to be serialized as JSON query tag
        """
        # Serialize the query tag to JSON
        query_tag_json = json.dumps(query_tag)
        # Escape single quotes for SQL by doubling them
        query_tag_escaped = query_tag_json.replace("'", "''")
        self._execute(f"ALTER SESSION SET QUERY_TAG = '{query_tag_escaped}'")

    def execute_query(
        self, query_num: int, run_num: int, warehouse_name: str, warehouse_size: str
    ) -> Dict[str, Any]:
        """
        Execute a single TPC-H query and capture metrics.

        Args:
            query_num: Query number (1-22)
            run_num: Run iteration (1-4)
            warehouse_name: Name of the warehouse
            warehouse_size: Size of the warehouse (SMALL, MEDIUM, XLARGE)

        Returns:
            Dictionary with query execution metrics
        """
        run_type = "cold" if run_num == 1 else "warm"

        # Create JSON structured query tag
        query_tag = {
            "app": APP_NAME,
            "workload_id": f"q{query_num:02d}",
            "run_id": self.run_id,
        }

        print(
            f"  [{run_type:4s}] Run {run_num}/4: Query {query_num:2d}",
            end=" ",
            flush=True,
        )

        # Load query SQL
        try:
            query_sql = self.load_query(query_num)
        except FileNotFoundError as e:
            print(f"✗ Error: {e}")
            return self._create_error_result(
                query_num,
                run_num,
                run_type,
                json.dumps(query_tag),
                warehouse_name,
                warehouse_size,
                str(e),
            )

        # Set query tag
        self.set_query_tag(query_tag)

        # Execute query and measure time
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat()
        error_message = None
        query_id = None
        rows_produced = 0

        try:
            # Execute asynchronously to get query ID immediately
            cursor = self._execute(query_sql, async_exec=True)
            query_id = cursor.sfqid

            # Wait for completion
            while self.conn.is_still_running(self.conn.get_query_status(query_id)):
                time.sleep(0.5)

            # Get results
            result_cursor = self.conn.cursor(DictCursor)
            result_cursor.get_results_from_sfqid(query_id)
            rows_produced = (
                result_cursor.rowcount
                if result_cursor.rowcount and result_cursor.rowcount > 0
                else 0
            )

        except Exception as e:
            error_message = str(e)
            print(f"✗ Error: {error_message[:50]}")

        execution_time = time.time() - start_time

        if error_message is None:
            print(f"✓ {execution_time:.2f}s ({rows_produced:,} rows)")

        # Create result record
        result = {
            "run_id": self.run_id,
            "timestamp": timestamp,
            "platform": "snowflake",
            "scenario": "primary",
            "warehouse_name": warehouse_name,
            "warehouse_size": warehouse_size,
            "query_num": query_num,
            "run_num": run_num,
            "run_type": run_type,
            "query_tag": json.dumps(query_tag),  # Store as JSON string in CSV
            "query_id": query_id or "",
            "execution_time_sec": round(execution_time, 3),
            "rows_produced": rows_produced,
            "error_message": error_message or "",
        }

        # Log to CSV immediately
        self._log_result(result)

        return result

    def _create_error_result(
        self,
        query_num: int,
        run_num: int,
        run_type: str,
        query_tag: str,
        warehouse_name: str,
        warehouse_size: str,
        error_message: str,
    ) -> Dict[str, Any]:
        """Create a result dictionary for an error case."""
        return {
            "run_id": self.run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "platform": "snowflake",
            "scenario": "primary",
            "warehouse_name": warehouse_name,
            "warehouse_size": warehouse_size,
            "query_num": query_num,
            "run_num": run_num,
            "run_type": run_type,
            "query_tag": query_tag,
            "query_id": "",
            "execution_time_sec": 0.0,
            "rows_produced": 0,
            "error_message": error_message,
        }

    def _init_csv(self):
        """Initialize CSV file for results - append mode or create new with headers."""
        file_exists = self.csv_file.exists()
        self.csv_handle = open(self.csv_file, "a", newline="")
        self.csv_writer = csv.DictWriter(self.csv_handle, fieldnames=CSV_COLUMNS)

        # Write header only if file is new
        if not file_exists:
            self.csv_writer.writeheader()
            print(f"✓ Created new results file: {self.csv_file}")
        else:
            print(f"✓ Appending results to: {self.csv_file}")

    def _log_result(self, result: Dict[str, Any]):
        """Log a single result to CSV."""
        if self.csv_writer:
            self.csv_writer.writerow(result)
            self.csv_handle.flush()  # Flush immediately to ensure data is written

    def _close_csv(self):
        """Close CSV file."""
        if self.csv_handle:
            self.csv_handle.close()

    def run_benchmark(
        self,
        warehouse_sizes: list[str] = None,
        query_nums: list[int] = None,
        num_runs: int = NUM_RUNS,
    ):
        """
        Run the complete benchmark.

        Args:
            warehouse_sizes: List of warehouse sizes to test (default: all)
            query_nums: List of query numbers to run (default: all 1-22)
            num_runs: Number of runs per query (default: 4)
        """
        # Default to all warehouses and queries if not specified
        if warehouse_sizes is None:
            warehouse_sizes = list(WAREHOUSES.keys())
        if query_nums is None:
            query_nums = list(range(1, NUM_QUERIES + 1))

        print("=" * 70)
        print("SNOWFLAKE TPC-H BENCHMARK")
        print("=" * 70)
        print(f"Run ID: {self.run_id}")
        print(f"Warehouses: {', '.join(warehouse_sizes)}")
        print(f"Queries: {len(query_nums)} queries")
        print(f"Runs per query: {num_runs} (1 cold + {num_runs - 1} warm)")
        print("=" * 70)

        self._init_csv()

        try:
            for warehouse_size in warehouse_sizes:
                warehouse_name = WAREHOUSES[warehouse_size]
                self.switch_warehouse(warehouse_name)

                print(f"\n{'=' * 70}")
                print(f"Testing warehouse: {warehouse_size.upper()} ({warehouse_name})")
                print(f"{'=' * 70}")

                for query_num in query_nums:
                    for run_num in range(1, num_runs + 1):
                        # Execute query
                        self.execute_query(
                            query_num=query_num,
                            run_num=run_num,
                            warehouse_name=warehouse_name,
                            warehouse_size=warehouse_size.upper(),
                        )

                        # If this was the first (cold) run, wait for warehouse to cool down
                        if run_num == 1 and run_num < num_runs:
                            print(
                                f"    Waiting {COLD_START_DELAY}s for warehouse cool-down..."
                            )
                            time.sleep(COLD_START_DELAY)

        finally:
            self._close_csv()

        print("\n" + "=" * 70)
        print("BENCHMARK COMPLETE")
        print("=" * 70)
        print(f"Results saved to: {self.csv_file}")
        print(f"Run ID: {self.run_id}")
        print("\nNext steps:")
        print(f"1. Wait {45} minutes for ACCOUNT_USAGE to populate")
        print(f"2. Run: uv run snowflake/enrich_results.py {self.csv_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Snowflake TPC-H Benchmark")
    parser.add_argument(
        "--warehouse",
        choices=["small", "medium", "xlarge"],
        action="append",
        help="Warehouse size(s) to test (can specify multiple times). Default: all",
    )
    parser.add_argument(
        "--queries",
        type=str,
        help='Comma-separated list of query numbers to run (e.g., "1,3,5"). Default: all (1-22)',
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=NUM_RUNS,
        help=f"Number of runs per query (default: {NUM_RUNS})",
    )
    parser.add_argument(
        "--connection",
        type=str,
        default=SNOWFLAKE_CONNECTION,
        help=f"Snowflake connection name (default: {SNOWFLAKE_CONNECTION})",
    )

    args = parser.parse_args()

    # Parse query numbers
    query_nums = None
    if args.queries:
        query_nums = [int(q.strip()) for q in args.queries.split(",")]

    # Run benchmark
    benchmark = SnowflakeBenchmark(connection_name=args.connection)

    try:
        benchmark.connect()
        benchmark.run_benchmark(
            warehouse_sizes=args.warehouse, query_nums=query_nums, num_runs=args.runs
        )
    finally:
        benchmark.disconnect()


if __name__ == "__main__":
    main()
