#!/usr/bin/env python3
"""
Databricks TPC-H Benchmark Runner

Executes TPC-H queries against Databricks SQL Warehouses and logs performance metrics.
"""

import json
import logging
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Set, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import sys

# Add parent directory to path to import from common
sys.path.insert(0, str(Path(__file__).parent.parent))

from databricks import sql
from common.connections import DatabricksConnection
from common.storage import BenchmarkStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

from config import (
    DATABRICKS_HOST,
    DATABRICKS_TOKEN,
    WAREHOUSES,
    CATALOG,
    SCHEMA,
    NUM_RUNS,
    NUM_QUERIES,
    SCALE_FACTOR,
    APP_NAME,
    QUERIES_DIR,
    RESULTS_DIR,
    DUCKDB_PATH,
)

# Global storage instance for thread-safe DuckDB writes
storage = BenchmarkStorage(DUCKDB_PATH)


class DatabricksBenchmark:
    """Manages Databricks TPC-H benchmark execution."""

    def __init__(
        self,
        warehouse_size: str = None,
        scale_factor: int = SCALE_FACTOR,
        run_id: str = None,
    ):
        """Initialize benchmark runner.

        Args:
            warehouse_size: Specific warehouse size for this instance (e.g., "xsmall", "small", "large")
            scale_factor: TPC-H scale factor (e.g., 100, 1000)
            run_id: Optional run ID to use (for parallel instances)
        """
        self.warehouse_size = warehouse_size
        self.scale_factor = scale_factor
        self.warehouse_id = WAREHOUSES.get(warehouse_size) if warehouse_size else None

        # Connection will be created when connect() is called
        self.dbx_connection: Optional[DatabricksConnection] = None
        self.conn: Optional[sql.client.Connection] = None

        # Use global storage instance for DuckDB
        self.storage = storage
        self.run_id = run_id if run_id else self._get_next_run_id()

        # Track warehouse state for run type classification
        self.warehouse_started = False  # True after first query executes
        self.queries_executed: Set[int] = (
            set()
        )  # Set of query numbers that have been executed

    def _get_next_run_id(self) -> str:
        """
        Get the next sequential run ID by reading existing DuckDB data.

        Returns:
            Zero-padded 3-digit run ID (e.g., "001", "002", "003")
        """
        try:
            # Query DuckDB for the maximum numeric run_id from both tables
            results_sf = self.storage.query("""
                SELECT MAX(CAST(run_id AS INTEGER)) as max_id
                FROM snowflake_results
                WHERE run_id ~ '^[0-9]+$'
            """)
            results_dbx = self.storage.query("""
                SELECT MAX(CAST(run_id AS INTEGER)) as max_id
                FROM databricks_results
                WHERE run_id ~ '^[0-9]+$'
            """)

            max_ids = []
            if results_sf and results_sf[0][0] is not None:
                max_ids.append(results_sf[0][0])
            if results_dbx and results_dbx[0][0] is not None:
                max_ids.append(results_dbx[0][0])

            if max_ids:
                max_run_id = max(max_ids)
                next_run_id = max_run_id + 1
                return f"{next_run_id:03d}"
            else:
                return "001"
        except Exception as e:
            logger.warning(f"Could not read existing run IDs: {e}. Starting from 001")
            return "001"

    def _get_warehouse_name(self, warehouse_size: str) -> str:
        """
        Get warehouse ID for the given size.

        Args:
            warehouse_size: Warehouse size key (e.g., "xsmall", "small", "large")

        Returns:
            Warehouse ID string
        """
        return WAREHOUSES[warehouse_size]

    def _stop_warehouse(self, warehouse_id: str):
        """
        Stop a warehouse using Databricks REST API.

        Args:
            warehouse_id: ID of the warehouse to stop
        """
        logger.info(f"Stopping warehouse: {warehouse_id}")

        try:
            # Clean hostname
            hostname = DATABRICKS_HOST.replace("https://", "").replace("http://", "")
            url = f"https://{hostname}/api/2.0/sql/warehouses/{warehouse_id}/stop"

            headers = {
                "Authorization": f"Bearer {DATABRICKS_TOKEN}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, headers=headers)
            response.raise_for_status()

            logger.info(f"✓ Stopped warehouse: {warehouse_id}")

            # Wait for warehouse to fully stop (check status)
            self._wait_for_warehouse_state(warehouse_id, "STOPPED")

        except Exception as e:
            logger.error(f"✗ Failed to stop warehouse {warehouse_id}: {e}")
            raise

    def _start_warehouse(self, warehouse_id: str):
        """
        Start a warehouse using Databricks REST API.

        Args:
            warehouse_id: ID of the warehouse to start
        """
        logger.info(f"Starting warehouse: {warehouse_id}")

        try:
            # Clean hostname
            hostname = DATABRICKS_HOST.replace("https://", "").replace("http://", "")
            url = f"https://{hostname}/api/2.0/sql/warehouses/{warehouse_id}/start"

            headers = {
                "Authorization": f"Bearer {DATABRICKS_TOKEN}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, headers=headers)
            response.raise_for_status()

            logger.info(f"✓ Started warehouse: {warehouse_id}")

            # Wait for warehouse to be ready
            self._wait_for_warehouse_state(warehouse_id, "RUNNING")

        except Exception as e:
            logger.error(f"✗ Failed to start warehouse {warehouse_id}: {e}")
            raise

    def _get_warehouse_state(self, warehouse_id: str) -> str:
        """
        Get current state of a warehouse.

        Args:
            warehouse_id: ID of the warehouse

        Returns:
            State string (e.g., "RUNNING", "STOPPED", "STARTING", "STOPPING")
        """
        # Clean hostname
        hostname = DATABRICKS_HOST.replace("https://", "").replace("http://", "")
        url = f"https://{hostname}/api/2.0/sql/warehouses/{warehouse_id}"

        headers = {
            "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json().get("state", "UNKNOWN")

    def _wait_for_warehouse_state(self, warehouse_id: str, target_state: str, timeout: int = 300):
        """
        Wait for warehouse to reach target state.

        Args:
            warehouse_id: ID of the warehouse
            target_state: Target state to wait for (e.g., "RUNNING", "STOPPED")
            timeout: Maximum time to wait in seconds
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            state = self._get_warehouse_state(warehouse_id)
            if state == target_state:
                logger.info(f"✓ Warehouse {warehouse_id} is {target_state}")
                return
            logger.debug(f"Waiting for warehouse {warehouse_id} to be {target_state} (current: {state})")
            time.sleep(5)

        raise TimeoutError(f"Warehouse {warehouse_id} did not reach {target_state} within {timeout}s")

    def connect(self):
        """Establish connection to Databricks using the configured warehouse."""
        if not self.warehouse_id:
            raise ValueError("warehouse_size must be specified to connect")

        # Use DatabricksConnection abstraction
        self.dbx_connection = DatabricksConnection(
            host=DATABRICKS_HOST,
            token=DATABRICKS_TOKEN,
            warehouse_id=self.warehouse_id,
            catalog=CATALOG,
            schema=SCHEMA,
        )
        self.dbx_connection.connect()

        # Store reference to the underlying connection for backward compatibility
        self.conn = self.dbx_connection.connection

    def disconnect(self):
        """Close Databricks connection."""
        if self.dbx_connection:
            self.dbx_connection.disconnect()
            self.conn = None

    def load_query(self, query_num: int) -> str:
        """Load TPC-H query from file."""
        query_file = QUERIES_DIR / f"q{query_num:02d}.sql"
        if not query_file.exists():
            raise FileNotFoundError(f"Query file not found: {query_file}")

        with open(query_file, "r") as f:
            query_sql = f.read().strip()

        return query_sql

    def execute_query(
        self, query_num: int, run_num: int, warehouse_id: str, warehouse_size: str
    ) -> Dict[str, Any]:
        """
        Execute a single TPC-H query and capture metrics.

        Args:
            query_num: Query number (1-22)
            run_num: Run iteration (1-4)
            warehouse_id: ID of the warehouse
            warehouse_size: Size of the warehouse (XSMALL, SMALL, LARGE)

        Returns:
            Dictionary with query execution metrics
        """
        # Determine run type based on warehouse state
        if not self.warehouse_started:
            # First query on this warehouse = cold
            run_type = "cold"
        elif query_num not in self.queries_executed:
            # Warehouse is running, but this query hasn't run yet = semi-warm
            run_type = "semi-warm"
        else:
            # This query has already run on this warehouse = warm
            run_type = "warm"

        # Create JSON structured query tag
        query_tag = {
            "app": APP_NAME,
            "workload_id": f"q{query_num:02d}",
            "run_id": self.run_id,
        }

        # Include warehouse size in log output for clarity in parallel execution
        wh_prefix = f"[{warehouse_size:6s}]" if warehouse_size else ""
        log_prefix = f"{wh_prefix} [{run_type:10s}] Run {run_num}/{NUM_RUNS}: Query {query_num:2d}"

        # Load query SQL
        try:
            query_sql = self.load_query(query_num)
        except FileNotFoundError as e:
            logger.error(f"{log_prefix} ✗ Error: {e}")
            return self._create_error_result(
                query_num,
                run_num,
                run_type,
                json.dumps(query_tag),
                warehouse_id,
                warehouse_size,
                str(e),
            )

        # Add query tag as SQL comment
        query_tag_json = json.dumps(query_tag)
        tagged_query = f"/* BENCHMARK: {query_tag_json} */\n{query_sql}"

        # Execute query and measure time
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat()
        error_message = None
        statement_id = None
        rows_produced = 0

        try:
            # Execute query
            cursor = self.conn.cursor()
            cursor.execute(tagged_query)

            # Get statement_id from cursor (if available)
            # Note: The Databricks SQL connector may expose this differently
            # We'll try to get it from the cursor or connection
            try:
                # Try to get statement_id from cursor attributes
                if hasattr(cursor, 'query_id'):
                    statement_id = cursor.query_id
                elif hasattr(cursor, '_op_handle') and hasattr(cursor._op_handle, 'statement_id'):
                    statement_id = cursor._op_handle.statement_id
            except Exception:
                # If we can't get the statement_id, that's okay
                pass

            # Fetch all results to get accurate row count
            results = cursor.fetchall()
            rows_produced = len(results)
            cursor.close()

        except Exception as e:
            error_message = str(e)
            logger.error(f"{log_prefix} ✗ Error: {error_message[:50]}")

        execution_time = time.time() - start_time

        if error_message is None:
            logger.info(
                f"{log_prefix} ✓ {execution_time:.2f}s ({rows_produced:,} rows)"
            )
            # Mark warehouse as started and track this query
            self.warehouse_started = True
            self.queries_executed.add(query_num)

        # Create result record
        result = {
            "run_id": self.run_id,
            "timestamp": timestamp,
            "platform": "databricks",
            "scenario": "primary",
            "warehouse_name": warehouse_id,
            "warehouse_size": warehouse_size,
            "query_num": query_num,
            "run_num": run_num,
            "run_type": run_type,
            "query_tag": json.dumps(query_tag),  # Store as JSON string
            "query_id": statement_id or "",
            "execution_time_sec": round(execution_time, 3),
            "rows_produced": rows_produced,
            "error_message": error_message or "",
        }

        # Log to DuckDB immediately
        self.storage.write_databricks_result(result)

        return result

    def _create_error_result(
        self,
        query_num: int,
        run_num: int,
        run_type: str,
        query_tag: str,
        warehouse_id: str,
        warehouse_size: str,
        error_message: str,
    ) -> Dict[str, Any]:
        """Create a result dictionary for an error case."""
        return {
            "run_id": self.run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "platform": "databricks",
            "scenario": "primary",
            "warehouse_name": warehouse_id,
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

    def run_warehouse_benchmark(
        self,
        warehouse_size: str,
        query_nums: list[int],
        num_runs: int,
    ) -> Dict[str, Any]:
        """
        Run benchmark for a single warehouse size.

        This method is designed to run in a separate thread for parallel execution.

        Args:
            warehouse_size: Warehouse size key (e.g., "xsmall", "small", "large")
            query_nums: List of query numbers to run
            num_runs: Number of runs per query

        Returns:
            Dictionary with execution summary
        """
        warehouse_id = self._get_warehouse_name(warehouse_size)

        logger.info(
            f"\n[{warehouse_size.upper()}] Starting benchmark on warehouse {warehouse_id}"
        )
        logger.info(f"[{warehouse_size.upper()}] Using warehouse: {warehouse_id}")

        try:
            # Execute all queries
            for query_num in query_nums:
                for run_num in range(1, num_runs + 1):
                    # Execute query (run_type is determined automatically)
                    self.execute_query(
                        query_num=query_num,
                        run_num=run_num,
                        warehouse_id=warehouse_id,
                        warehouse_size=warehouse_size.upper(),
                    )

            logger.info(
                f"\n[{warehouse_size.upper()}] ✓ Completed all queries on {warehouse_id}"
            )

            return {
                "warehouse_size": warehouse_size,
                "warehouse_id": warehouse_id,
                "queries_completed": len(query_nums) * num_runs,
                "success": True,
            }

        except Exception as e:
            logger.error(f"\n[{warehouse_size.upper()}] ✗ Error: {e}")
            return {
                "warehouse_size": warehouse_size,
                "warehouse_id": warehouse_id,
                "success": False,
                "error": str(e),
            }

    def run_benchmark(
        self,
        warehouse_sizes: list[str] = None,
        query_nums: list[int] = None,
        num_runs: int = NUM_RUNS,
        parallel: bool = True,
        stop_start_warehouses: bool = False,
    ):
        """
        Run the complete benchmark across multiple warehouse sizes.

        Args:
            warehouse_sizes: List of warehouse sizes to test (default: all)
            query_nums: List of query numbers to run (default: all 1-22)
            num_runs: Number of runs per query (default: 4)
            parallel: If True, run warehouses in parallel (default: True)
            stop_start_warehouses: If True, stop/start warehouses for cold runs (default: False)
        """
        # Default to all warehouses and queries if not specified
        if warehouse_sizes is None:
            warehouse_sizes = list(WAREHOUSES.keys())
        if query_nums is None:
            query_nums = list(range(1, NUM_QUERIES + 1))

        logger.info("=" * 70)
        logger.info("DATABRICKS TPC-H BENCHMARK")
        logger.info("=" * 70)
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"Scale Factor: SF{self.scale_factor} (~{self.scale_factor}GB)")
        logger.info(f"Warehouses: {', '.join(warehouse_sizes)}")
        logger.info(f"Queries: {len(query_nums)} queries")
        logger.info(f"Runs per query: {num_runs}")
        logger.info(f"Execution mode: {'Parallel' if parallel else 'Sequential'}")
        logger.info(f"Stop/start warehouses: {stop_start_warehouses}")
        logger.info(
            f"Total query executions: {len(warehouse_sizes) * len(query_nums) * num_runs}"
        )
        logger.info("=" * 70)

        # Stop all warehouses if requested (for true cold start)
        if stop_start_warehouses:
            logger.info("\n" + "=" * 70)
            logger.info("STOPPING WAREHOUSES FOR COLD START")
            logger.info("=" * 70)
            for warehouse_size in warehouse_sizes:
                warehouse_id = WAREHOUSES[warehouse_size]
                self._stop_warehouse(warehouse_id)
            logger.info("=" * 70)

        try:
            if not parallel:
                # Sequential execution
                for warehouse_size in warehouse_sizes:
                    # Create instance for this warehouse
                    instance = DatabricksBenchmark(
                        warehouse_size=warehouse_size,
                        scale_factor=self.scale_factor,
                        run_id=self.run_id,
                    )
                    instance.connect()
                    try:
                        instance.run_warehouse_benchmark(warehouse_size, query_nums, num_runs)
                    finally:
                        instance.disconnect()
            else:
                # Parallel execution across warehouses
                logger.info("\n🚀 Launching parallel execution across all warehouses...")

                # Create separate benchmark instances for each warehouse
                # Each needs its own connection but shares the same run_id
                benchmark_instances = {}
                for warehouse_size in warehouse_sizes:
                    instance = DatabricksBenchmark(
                        warehouse_size=warehouse_size,
                        scale_factor=self.scale_factor,
                        run_id=self.run_id,  # Share the same run_id
                    )
                    benchmark_instances[warehouse_size] = instance

                try:
                    # Connect all instances
                    for warehouse_size, instance in benchmark_instances.items():
                        instance.connect()

                    # Use ThreadPoolExecutor to run warehouses in parallel
                    with ThreadPoolExecutor(max_workers=len(warehouse_sizes)) as executor:
                        # Submit all warehouse benchmarks
                        future_to_warehouse = {
                            executor.submit(
                                instance.run_warehouse_benchmark,
                                warehouse_size,
                                query_nums,
                                num_runs,
                            ): warehouse_size
                            for warehouse_size, instance in benchmark_instances.items()
                        }

                        # Wait for completion and collect results
                        results = {}
                        for future in as_completed(future_to_warehouse):
                            warehouse_size = future_to_warehouse[future]
                            try:
                                result = future.result()
                                results[warehouse_size] = result
                            except Exception as e:
                                logger.error(
                                    f"\n✗ Exception in {warehouse_size} warehouse: {e}"
                                )
                                results[warehouse_size] = {
                                    "warehouse_size": warehouse_size,
                                    "success": False,
                                    "error": str(e),
                                }

                finally:
                    # Disconnect all instances
                    for instance in benchmark_instances.values():
                        instance.disconnect()

        finally:
            pass  # No warehouse cleanup needed (using pre-created warehouses)

        logger.info("\n" + "=" * 70)
        logger.info("BENCHMARK COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Results saved to: {DUCKDB_PATH}")
        logger.info(f"Run ID: {self.run_id}")
        logger.info("\nNext steps:")
        logger.info("1. Query results from DuckDB")
        logger.info("2. Compare with Snowflake results")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Databricks TPC-H Benchmark")
    parser.add_argument(
        "--warehouse",
        choices=list(WAREHOUSES.keys()),
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
        "--sequential",
        action="store_true",
        help="Run warehouses sequentially instead of in parallel (default: parallel)",
    )
    parser.add_argument(
        "--stop-start",
        action="store_true",
        help="Stop and start warehouses for true cold runs (default: False)",
    )
    parser.add_argument(
        "--scale-factor",
        type=int,
        default=SCALE_FACTOR,
        help=f"TPC-H scale factor (default: {SCALE_FACTOR}). Common values: 100 (100GB), 1000 (1TB), 10000 (10TB)",
    )

    args = parser.parse_args()

    # Parse query numbers
    query_nums = None
    if args.queries:
        query_nums = [int(q.strip()) for q in args.queries.split(",")]

    # Run benchmark
    benchmark = DatabricksBenchmark(scale_factor=args.scale_factor)

    benchmark.run_benchmark(
        warehouse_sizes=args.warehouse,
        query_nums=query_nums,
        num_runs=args.runs,
        parallel=not args.sequential,
        stop_start_warehouses=args.stop_start,
    )


if __name__ == "__main__":
    main()
