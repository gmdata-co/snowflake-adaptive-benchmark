#!/usr/bin/env python3
"""
Snowflake TPC-H Benchmark Runner

Executes TPC-H queries against Snowflake and logs performance metrics.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Set, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import sys

# Add parent directory to path to import from common
sys.path.insert(0, str(Path(__file__).parent.parent))

import snowflake.connector
from snowflake.connector import DictCursor
from common.connections import SnowflakeConnection
from common.storage import BenchmarkStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

from config import (
    SNOWFLAKE_CONNECTION,
    SNOWFLAKE_ROLE,
    SNOWFLAKE_DATABASE,
    SNOWFLAKE_SCHEMA,
    WAREHOUSE_SIZES,
    WAREHOUSE_SIZE_MAP,
    WAREHOUSE_PREFIX,
    WAREHOUSE_AUTO_SUSPEND,
    WAREHOUSE_AUTO_RESUME,
    WAREHOUSE_INITIALLY_SUSPENDED,
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


class SnowflakeBenchmark:
    """Manages Snowflake TPC-H benchmark execution."""

    def __init__(
        self,
        connection_name: str = SNOWFLAKE_CONNECTION,
        warehouse_size: str = None,
        scale_factor: int = SCALE_FACTOR,
        run_id: str = None,
    ):
        """Initialize benchmark runner.

        Args:
            connection_name: Name of connection from ~/.snowflake/connections.toml
            warehouse_size: Specific warehouse size for this instance (e.g., "small", "medium", "xlarge")
            scale_factor: TPC-H scale factor (e.g., 100, 1000)
            run_id: Optional run ID to use (for parallel instances)
        """
        self.connection_name = connection_name
        self.warehouse_size = warehouse_size
        self.scale_factor = scale_factor

        # Use SnowflakeConnection abstraction
        self.sf_connection = SnowflakeConnection(
            connection_name=connection_name,
            role=SNOWFLAKE_ROLE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
        )
        self.conn: Optional[snowflake.connector.SnowflakeConnection] = None

        # Use global storage instance for DuckDB
        self.storage = storage
        self.run_id = run_id if run_id else self._get_next_run_id()

        # Track warehouses created by this benchmark (for cleanup)
        self.created_warehouses: List[str] = []

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
            # Query DuckDB for the maximum numeric run_id
            results = self.storage.query("""
                SELECT MAX(CAST(run_id AS INTEGER)) as max_id
                FROM snowflake_results
                WHERE run_id ~ '^[0-9]+$'
            """)

            if results and results[0][0] is not None:
                max_run_id = results[0][0]
                next_run_id = max_run_id + 1
                return f"{next_run_id:03d}"
            else:
                return "001"
        except Exception as e:
            logger.warning(f"Could not read existing run IDs: {e}. Starting from 001")
            return "001"

    def _get_warehouse_name(self, warehouse_size: str) -> str:
        """
        Generate warehouse name with run_id suffix.

        Args:
            warehouse_size: Warehouse size key (e.g., "small", "medium", "xlarge")

        Returns:
            Full warehouse name (e.g., "BENCHMARK_WH_MEDIUM_001")
        """
        size_upper = WAREHOUSE_SIZE_MAP[warehouse_size]
        return f"{WAREHOUSE_PREFIX}_{size_upper}_{self.run_id}"

    def _create_warehouse(self, warehouse_size: str) -> str:
        """
        Create a warehouse for this benchmark run.

        Args:
            warehouse_size: Warehouse size key (e.g., "small", "medium", "xlarge")

        Returns:
            Name of the created warehouse
        """
        warehouse_name = self._get_warehouse_name(warehouse_size)
        size_upper = WAREHOUSE_SIZE_MAP[warehouse_size]

        logger.info(f"Creating warehouse: {warehouse_name} (size: {size_upper})")

        # Need to use SYSADMIN role to create warehouse
        self._execute("USE ROLE SYSADMIN")

        create_sql = f"""CREATE WAREHOUSE IF NOT EXISTS {warehouse_name}
            WITH
            WAREHOUSE_SIZE = '{size_upper}'
            AUTO_SUSPEND = {WAREHOUSE_AUTO_SUSPEND}
            AUTO_RESUME = {str(WAREHOUSE_AUTO_RESUME).upper()}
            INITIALLY_SUSPENDED = {str(WAREHOUSE_INITIALLY_SUSPENDED).upper()}
            COMMENT = 'Ephemeral warehouse for benchmark run {self.run_id}'"""

        self._execute(create_sql)

        # Grant all privileges to BENCHMARK role so it can use and drop the warehouse
        grant_sql = f"GRANT ALL ON WAREHOUSE {warehouse_name} TO ROLE {SNOWFLAKE_ROLE}"
        self._execute(grant_sql)

        # Switch back to BENCHMARK role
        self._execute(f"USE ROLE {SNOWFLAKE_ROLE}")

        logger.info(f"✓ Created warehouse: {warehouse_name}")
        self.created_warehouses.append(warehouse_name)

        return warehouse_name

    def _destroy_warehouse(self, warehouse_name: str):
        """
        Destroy a warehouse created by this benchmark.

        Args:
            warehouse_name: Name of warehouse to destroy
        """
        logger.info(f"Destroying warehouse: {warehouse_name}")

        try:
            drop_sql = f"DROP WAREHOUSE IF EXISTS {warehouse_name}"
            self._execute(drop_sql)
            logger.info(f"✓ Destroyed warehouse: {warehouse_name}")
        except Exception as e:
            logger.error(f"✗ Failed to destroy warehouse {warehouse_name}: {e}")

    def _create_all_warehouses(self, warehouse_sizes: List[str]):
        """
        Create all warehouses needed for this benchmark run.

        Args:
            warehouse_sizes: List of warehouse size keys to create
        """
        logger.info("\n" + "=" * 70)
        logger.info("CREATING WAREHOUSES")
        logger.info("=" * 70)

        for warehouse_size in warehouse_sizes:
            self._create_warehouse(warehouse_size)

        logger.info("=" * 70)

    def _destroy_all_warehouses(self):
        """Destroy all warehouses created by this benchmark run."""
        if not self.created_warehouses:
            return

        logger.info("\n" + "=" * 70)
        logger.info("CLEANING UP WAREHOUSES")
        logger.info("=" * 70)

        for warehouse_name in self.created_warehouses:
            self._destroy_warehouse(warehouse_name)

        logger.info("=" * 70)

    def connect(self):
        """Establish connection to Snowflake using the configured connection."""
        # Use SnowflakeConnection abstraction
        self.sf_connection.connect()

        # Store reference to the underlying connection for backward compatibility
        self.conn = self.sf_connection.connection

    def disconnect(self):
        """Close Snowflake connection."""
        if self.sf_connection:
            self.sf_connection.disconnect()
            self.conn = None

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
        # Don't print here - will be printed in run_warehouse_benchmark with proper context
        self._execute(f"USE WAREHOUSE {warehouse_name}")

    def load_query(self, query_num: int) -> str:
        """Load TPC-H query from file and substitute the scale factor."""
        query_file = QUERIES_DIR / f"q{query_num:02d}.sql"
        if not query_file.exists():
            raise FileNotFoundError(f"Query file not found: {query_file}")

        with open(query_file, "r") as f:
            query_sql = f.read().strip()

        # Replace the scale factor in the query (e.g., TPCH_SF100 -> TPCH_SF1000)
        query_sql = query_sql.replace("TPCH_SF100", f"TPCH_SF{self.scale_factor}")

        return query_sql

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
        # Use logger but print without newline by constructing the message and printing later
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
            # Fetch all results to get accurate row count
            # Note: timing is already complete, so this doesn't affect metrics
            results = result_cursor.fetchall()
            rows_produced = len(results)

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

        # Log to DuckDB immediately
        self.storage.write_result(result)

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
            warehouse_size: Warehouse size key (e.g., "small", "medium", "xlarge")
            query_nums: List of query numbers to run
            num_runs: Number of runs per query

        Returns:
            Dictionary with execution summary
        """
        warehouse_name = self._get_warehouse_name(warehouse_size)

        logger.info(
            f"\n[{warehouse_size.upper()}] Starting benchmark on {warehouse_name}"
        )
        logger.info(f"[{warehouse_size.upper()}] Using warehouse: {warehouse_name}")

        try:
            # Switch to this warehouse
            self.switch_warehouse(warehouse_name)

            # Execute all queries
            for query_num in query_nums:
                for run_num in range(1, num_runs + 1):
                    # Execute query (run_type is determined automatically)
                    self.execute_query(
                        query_num=query_num,
                        run_num=run_num,
                        warehouse_name=warehouse_name,
                        warehouse_size=warehouse_size.upper(),
                    )

            logger.info(
                f"\n[{warehouse_size.upper()}] ✓ Completed all queries on {warehouse_name}"
            )

            return {
                "warehouse_size": warehouse_size,
                "warehouse_name": warehouse_name,
                "queries_completed": len(query_nums) * num_runs,
                "success": True,
            }

        except Exception as e:
            logger.error(f"\n[{warehouse_size.upper()}] ✗ Error: {e}")
            return {
                "warehouse_size": warehouse_size,
                "warehouse_name": warehouse_name,
                "success": False,
                "error": str(e),
            }

    def run_benchmark(
        self,
        warehouse_sizes: list[str] = None,
        query_nums: list[int] = None,
        num_runs: int = NUM_RUNS,
        parallel: bool = True,
    ):
        """
        Run the complete benchmark across multiple warehouse sizes.

        Args:
            warehouse_sizes: List of warehouse sizes to test (default: all)
            query_nums: List of query numbers to run (default: all 1-22)
            num_runs: Number of runs per query (default: 4)
            parallel: If True, run warehouses in parallel (default: True)
        """
        # Default to all warehouses and queries if not specified
        if warehouse_sizes is None:
            warehouse_sizes = WAREHOUSE_SIZES
        if query_nums is None:
            query_nums = list(range(1, NUM_QUERIES + 1))

        logger.info("=" * 70)
        logger.info("SNOWFLAKE TPC-H BENCHMARK")
        logger.info("=" * 70)
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"Scale Factor: SF{self.scale_factor} (~{self.scale_factor}GB)")
        logger.info(f"Warehouses: {', '.join(warehouse_sizes)}")
        logger.info(f"Queries: {len(query_nums)} queries")
        logger.info(f"Runs per query: {num_runs}")
        logger.info(f"Execution mode: {'Parallel' if parallel else 'Sequential'}")
        logger.info(
            f"Total query executions: {len(warehouse_sizes) * len(query_nums) * num_runs}"
        )
        logger.info("=" * 70)

        # Connect to Snowflake first (needed for warehouse creation)
        if not parallel:
            self.connect()

        # DuckDB is initialized globally, no need for _init_csv()

        # Create warehouses after connection
        if not parallel:
            self._create_all_warehouses(warehouse_sizes)

        try:
            if not parallel:
                # Sequential execution
                for warehouse_size in warehouse_sizes:
                    self.run_warehouse_benchmark(warehouse_size, query_nums, num_runs)
            else:
                # Parallel execution across warehouses
                logger.info("\n🚀 Launching parallel execution across all warehouses...")

                # Connect the main instance first to create warehouses
                self.connect()
                self._create_all_warehouses(warehouse_sizes)

                # Create separate benchmark instances for each warehouse
                # Each needs its own connection but shares the same run_id and CSV file
                benchmark_instances = {}
                for warehouse_size in warehouse_sizes:
                    instance = SnowflakeBenchmark(
                        connection_name=self.connection_name,
                        warehouse_size=warehouse_size,
                        scale_factor=self.scale_factor,
                        run_id=self.run_id,  # Share the same run_id
                    )
                    # Share warehouse list for cleanup
                    instance.created_warehouses = self.created_warehouses
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
                    # Disconnect and close all instances
                    for instance in benchmark_instances.values():
                        instance._close_csv()
                        instance.disconnect()

                    # Destroy warehouses before disconnecting main instance
                    self._destroy_all_warehouses()
                    self.disconnect()

        finally:
            # Always clean up warehouses (sequential mode only, parallel already handled)
            if not parallel:
                self._close_csv()
                self._destroy_all_warehouses()

        logger.info("\n" + "=" * 70)
        logger.info("BENCHMARK COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Results saved to: {self.csv_file}")
        logger.info(f"Run ID: {self.run_id}")
        logger.info("\nNext steps:")
        logger.info("1. Wait 45 minutes for ACCOUNT_USAGE to populate")
        logger.info(f"2. Run: uv run snowflake/enrich_results.py {self.csv_file}")


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
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run warehouses sequentially instead of in parallel (default: parallel)",
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
    benchmark = SnowflakeBenchmark(
        connection_name=args.connection, scale_factor=args.scale_factor
    )

    try:
        if not args.sequential:
            # Parallel mode - don't connect main instance, it will create separate instances
            benchmark.run_benchmark(
                warehouse_sizes=args.warehouse,
                query_nums=query_nums,
                num_runs=args.runs,
                parallel=True,
            )
        else:
            # Sequential mode - connect and run on main instance
            benchmark.connect()
            benchmark.run_benchmark(
                warehouse_sizes=args.warehouse,
                query_nums=query_nums,
                num_runs=args.runs,
                parallel=False,
            )
    finally:
        if args.sequential:
            benchmark.disconnect()


if __name__ == "__main__":
    main()
