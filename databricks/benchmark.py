#!/usr/bin/env python3
"""
Databricks TPC-H Benchmark Runner

Executes TPC-H queries against Databricks SQL Warehouses and logs performance metrics.
"""

from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import sys
import time

# Add parent directory to path to import from common
sys.path.insert(0, str(Path(__file__).parent.parent))

from databricks import sql
from common.connections import DatabricksConnection
from common.storage import BenchmarkStorage
from common.logging_config import get_logger
from .config import (
    DATABRICKS_HOST,
    DATABRICKS_TOKEN,
    CATALOG,
    SCHEMA,
    NUM_RUNS,
    NUM_QUERIES,
    SCALE_FACTOR,
    DUCKDB_PATH,
    WAREHOUSE_SIZES,
)
from .warehouse_manager import WarehouseManager
from .query_executor import QueryExecutor

logger = get_logger(__name__)

# Global storage instance for thread-safe DuckDB writes
storage = BenchmarkStorage(DUCKDB_PATH)


class DatabricksBenchmark:
    """Manages Databricks TPC-H benchmark execution."""

    def __init__(
        self,
        scale_factor: int = SCALE_FACTOR,
        run_id: str = None,
    ):
        """Initialize benchmark runner.

        Args:
            scale_factor: TPC-H scale factor (e.g., 100, 1000)
            run_id: Optional run ID to use (for parallel instances or unified scenarios)
        """
        self.scale_factor = scale_factor

        # Connection will be created when connect() is called
        self.dbx_connection: Optional[DatabricksConnection] = None
        self.conn: Optional[sql.client.Connection] = None

        # Use global storage instance for DuckDB
        self.storage = storage
        self.run_id = run_id if run_id else self._get_next_run_id()

        # Managers (initialized when needed)
        self.warehouse_manager: Optional[WarehouseManager] = None
        self.query_executor: Optional[QueryExecutor] = None

    def _get_next_run_id(self) -> str:
        """
        Get the next sequential run ID by reading existing DuckDB data.

        Returns:
            Zero-padded 3-digit run ID (e.g., "001", "002", "003")
        """
        return self.storage.get_next_run_id()

    def connect(self, warehouse_id: str):
        """Establish connection to Databricks and initialize query executor.

        Args:
            warehouse_id: Warehouse ID to connect to
        """
        # Use DatabricksConnection abstraction
        self.dbx_connection = DatabricksConnection(
            host=DATABRICKS_HOST,
            token=DATABRICKS_TOKEN,
            warehouse_id=warehouse_id,
            catalog=CATALOG,
            schema=SCHEMA,
        )
        self.dbx_connection.connect()

        # Store reference to the underlying connection
        self.conn = self.dbx_connection.connection

        # Initialize query executor (warehouse manager doesn't need connection)
        self.query_executor = QueryExecutor(
            connection=self.conn,
            storage=self.storage,
            run_id=self.run_id,
            scale_factor=self.scale_factor,
        )

    def disconnect(self):
        """Close Databricks connection."""
        if self.dbx_connection:
            self.dbx_connection.disconnect()
            self.conn = None
            self.query_executor = None

    def run_warehouse_benchmark(
        self,
        warehouse_size: str,
        warehouse_id: str,
        query_nums: list[int],
        num_runs: int,
        scenario: str = "normal",
    ):
        """
        Run benchmark for a single warehouse size.

        This method is designed to run in a separate thread for parallel execution.

        Args:
            warehouse_size: Warehouse size key (e.g., "small", "medium", "large")
            warehouse_id: ID of the warehouse to use
            query_nums: List of query numbers to run
            num_runs: Number of runs per query
            scenario: Scenario name (e.g., "normal", "coldstart", "concurrent")
        """
        logger.info(
            f"\n[{warehouse_size.upper()}] Starting benchmark on warehouse {warehouse_id}"
        )
        logger.info(f"[{warehouse_size.upper()}] Using warehouse: {warehouse_id}")

        # Record wall clock start time for this warehouse
        self.storage.record_run_start(
            run_id=self.run_id,
            platform="databricks",
            scenario=scenario,
            warehouse_size=warehouse_size.upper(),
            warehouse_name=warehouse_id,
        )

        try:
            # Execute all queries
            for query_num in query_nums:
                for run_num in range(1, num_runs + 1):
                    # Execute query (run_type is determined automatically)
                    self.query_executor.execute_query(
                        query_num=query_num,
                        run_num=run_num,
                        warehouse_id=warehouse_id,
                        warehouse_size=warehouse_size.upper(),
                        scenario=scenario,
                    )

            logger.info(
                f"\n[{warehouse_size.upper()}] ✅ Completed all queries on {warehouse_id}"
            )

        except Exception as e:
            logger.error(f"\n[{warehouse_size.upper()}] ❌ Error: {e}")
            raise
        finally:
            # Record wall clock end time for this warehouse
            self.storage.record_run_end(
                run_id=self.run_id,
                platform="databricks",
                scenario=scenario,
                warehouse_size=warehouse_size.upper(),
            )

    def run_cold_start_trial(
        self,
        warehouse_sizes: list[str] = None,
        query_nums: list[int] = None,
    ):
        """
        Run cold start trial: stop warehouse between each query execution.

        This measures true cold start performance by stopping the warehouse
        after each query, forcing it to start from a completely cold state
        for the next query.

        Args:
            warehouse_sizes: List of warehouse sizes to test (default: ["small"])
            query_nums: List of query numbers to run (default: [1, 3, 5, 10, 18])
        """
        scenario = "coldstart"

        if warehouse_sizes is None:
            warehouse_sizes = ["small"]
        if query_nums is None:
            query_nums = [1, 3, 5, 10, 18]

        logger.info("=" * 70)
        logger.info("DATABRICKS COLD START TRIAL")
        logger.info("=" * 70)
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"Scenario: {scenario}")
        logger.info(f"Scale Factor: SF{self.scale_factor} (~{self.scale_factor}GB)")
        logger.info(f"Warehouses: {', '.join(warehouse_sizes)}")
        logger.info(f"Queries: {query_nums}")
        logger.info("=" * 70)

        # Initialize warehouse manager
        self.warehouse_manager = WarehouseManager(run_id=self.run_id)

        # Create warehouses with scenario in name
        warehouse_id_map = self.warehouse_manager.create_all_warehouses(
            warehouse_sizes, scenario
        )

        try:
            # Execute each query with stop/start cycle for each warehouse
            for warehouse_size in warehouse_sizes:
                warehouse_id = warehouse_id_map[warehouse_size]

                logger.info(
                    f"\n[{warehouse_size.upper()}] Starting COLD START trial on warehouse {warehouse_id}"
                )
                logger.info(f"[{warehouse_size.upper()}] Queries: {query_nums}")

                # Record wall clock start time for this warehouse
                self.storage.record_run_start(
                    run_id=self.run_id,
                    platform="databricks",
                    scenario=scenario,
                    warehouse_size=warehouse_size.upper(),
                    warehouse_name=warehouse_id,
                )

                # Connect for this warehouse
                self.connect(warehouse_id=warehouse_id)

                try:
                    for query_num in query_nums:
                        # Start warehouse before query
                        logger.info(
                            f"\n[{warehouse_size.upper()}] Starting warehouse for query {query_num}"
                        )
                        self.warehouse_manager.start_warehouse(warehouse_id)

                        # Execute query once (run_num=1, always cold start)
                        self.query_executor.execute_query(
                            query_num=query_num,
                            run_num=1,
                            warehouse_id=warehouse_id,
                            warehouse_size=warehouse_size.upper(),
                            scenario=scenario,
                            force_run_type="cold",  # Force cold run type
                        )

                        # Stop warehouse after query (don't wait for it to fully stop)
                        logger.info(
                            f"[{warehouse_size.upper()}] Stopping warehouse after query {query_num}"
                        )
                        self.warehouse_manager.stop_warehouse(
                            warehouse_id, wait_for_stopped=False
                        )

                    logger.info(
                        f"\n[{warehouse_size.upper()}] ✅ Completed COLD START trial on {warehouse_id}"
                    )
                finally:
                    self.disconnect()
                    # Record wall clock end time for this warehouse
                    self.storage.record_run_end(
                        run_id=self.run_id,
                        platform="databricks",
                        scenario=scenario,
                        warehouse_size=warehouse_size.upper(),
                    )

        finally:
            # Always clean up warehouses
            self.warehouse_manager.destroy_all_warehouses()

        logger.info("\n" + "=" * 70)
        logger.info("COLD START TRIAL COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Results saved to: {DUCKDB_PATH}")
        logger.info(f"Run ID: {self.run_id}")

    def run_concurrent_benchmark(
        self,
        warehouse_sizes: list[str] = None,
        query_nums: list[int] = None,
    ):
        """
        Run concurrent benchmark: execute all queries in parallel on the same warehouse.

        This measures performance under concurrent load by executing all queries
        simultaneously using a multi-cluster warehouse.

        Args:
            warehouse_sizes: List of warehouse sizes to test (default: ["small"])
            query_nums: List of query numbers to run (default: all 1-22)
        """
        scenario = "concurrent"

        if warehouse_sizes is None:
            warehouse_sizes = ["small"]
        if query_nums is None:
            query_nums = list(range(1, NUM_QUERIES + 1))

        logger.info("=" * 70)
        logger.info("DATABRICKS CONCURRENT BENCHMARK")
        logger.info("=" * 70)
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"Scenario: {scenario}")
        logger.info(f"Scale Factor: SF{self.scale_factor} (~{self.scale_factor}GB)")
        logger.info(f"Warehouses: {', '.join(warehouse_sizes)}")
        logger.info(f"Queries: {query_nums} ({len(query_nums)} queries)")
        logger.info("Execution: All queries in parallel (concurrent)")
        logger.info("Multi-cluster: max_num_clusters=4")
        logger.info("=" * 70)

        # Initialize warehouse manager
        self.warehouse_manager = WarehouseManager(run_id=self.run_id)

        # Create warehouses with multi-cluster configuration
        warehouse_id_map = self.warehouse_manager.create_all_warehouses(
            warehouse_sizes, scenario, max_num_clusters=4
        )

        try:
            # Execute concurrent queries for each warehouse
            for warehouse_size in warehouse_sizes:
                warehouse_id = warehouse_id_map[warehouse_size]

                logger.info(
                    f"\n[{warehouse_size.upper()}] Starting CONCURRENT benchmark on warehouse {warehouse_id}"
                )
                logger.info(
                    f"[{warehouse_size.upper()}] Executing {len(query_nums)} queries in parallel"
                )

                # Record wall clock start time for this warehouse
                self.storage.record_run_start(
                    run_id=self.run_id,
                    platform="databricks",
                    scenario=scenario,
                    warehouse_size=warehouse_size.upper(),
                    warehouse_name=warehouse_id,
                )

                # Create separate benchmark instances for each query
                # Each needs its own connection for concurrent execution
                benchmark_instances = []
                for _ in query_nums:
                    instance = DatabricksBenchmark(
                        scale_factor=self.scale_factor,
                        run_id=self.run_id,  # Share the same run_id
                    )
                    # Share warehouse manager
                    instance.warehouse_manager = self.warehouse_manager
                    benchmark_instances.append(instance)

                try:
                    # Connect all instances
                    for instance in benchmark_instances:
                        instance.connect(warehouse_id=warehouse_id)

                    # Execute all queries concurrently using ThreadPoolExecutor
                    logger.info(
                        f"\n[{warehouse_size.upper()}] 🚀 Launching {len(query_nums)} concurrent queries..."
                    )

                    with ThreadPoolExecutor(max_workers=len(query_nums)) as executor:
                        # Submit all queries for concurrent execution
                        future_to_query = {}
                        for idx, query_num in enumerate(query_nums):
                            instance = benchmark_instances[idx]
                            future = executor.submit(
                                self._execute_single_query,
                                instance,
                                query_num,
                                warehouse_id,
                                warehouse_size,
                                scenario,
                            )
                            future_to_query[future] = query_num

                        # Wait for completion and collect results
                        for future in as_completed(future_to_query):
                            query_num = future_to_query[future]
                            try:
                                future.result()
                                logger.info(
                                    f"[{warehouse_size.upper()}] ✓ Query {query_num} completed"
                                )
                            except Exception as e:
                                logger.error(
                                    f"\n[{warehouse_size.upper()}] ❌ Query {query_num} failed: {e}"
                                )

                finally:
                    # Disconnect all instances
                    logger.info("\n🔌 Closing all connections...")
                    for instance in benchmark_instances:
                        instance.disconnect()

                    # Add a small delay to ensure connections are fully closed
                    time.sleep(3)

                    # Record wall clock end time for this warehouse
                    self.storage.record_run_end(
                        run_id=self.run_id,
                        platform="databricks",
                        scenario=scenario,
                        warehouse_size=warehouse_size.upper(),
                    )

                logger.info(
                    f"\n[{warehouse_size.upper()}] ✅ Completed CONCURRENT benchmark on {warehouse_id}"
                )

        finally:
            # Always clean up warehouses
            self.warehouse_manager.destroy_all_warehouses()

        logger.info("\n" + "=" * 70)
        logger.info("CONCURRENT BENCHMARK COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Results saved to: {DUCKDB_PATH}")
        logger.info(f"Run ID: {self.run_id}")

    def _execute_single_query(
        self,
        instance: "DatabricksBenchmark",
        query_num: int,
        warehouse_id: str,
        warehouse_size: str,
        scenario: str,
    ):
        """
        Execute a single query (helper for concurrent execution).

        Args:
            instance: DatabricksBenchmark instance with its own connection
            query_num: Query number to execute
            warehouse_id: ID of the warehouse to use
            warehouse_size: Warehouse size key
            scenario: Scenario name
        """
        # Execute the query once (run_num=1)
        instance.query_executor.execute_query(
            query_num=query_num,
            run_num=1,
            warehouse_id=warehouse_id,
            warehouse_size=warehouse_size.upper(),
            scenario=scenario,
        )

    def run_ctas_benchmark(
        self,
        warehouse_sizes: list[str] = None,
    ):
        """
        Run CTAS benchmark: Execute the special ctas.sql query as CREATE TABLE AS SELECT.

        This creates a large denormalized table by joining all TPC-H tables (~6B rows at SF1000).
        Tables are created during execution (tracked in metrics), then dropped
        after warehouse destruction (not counted in metrics).

        Args:
            warehouse_sizes: List of warehouse sizes to test (default: ["small"])
        """
        scenario = "ctas"

        if warehouse_sizes is None:
            warehouse_sizes = ["small"]

        logger.info("=" * 70)
        logger.info("DATABRICKS CTAS BENCHMARK")
        logger.info("=" * 70)
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"Scenario: {scenario}")
        logger.info(f"Scale Factor: SF{self.scale_factor} (~{self.scale_factor}GB)")
        logger.info(f"Warehouses: {', '.join(warehouse_sizes)}")
        logger.info("Query: ctas.sql (denormalized join of all TPC-H tables)")
        logger.info("Execution: Sequential (CREATE TABLE AS SELECT)")
        logger.info("=" * 70)

        # Initialize warehouse manager
        self.warehouse_manager = WarehouseManager(run_id=self.run_id)

        # Create warehouses with scenario in name
        warehouse_id_map = self.warehouse_manager.create_all_warehouses(
            warehouse_sizes, scenario
        )

        # Track created tables for cleanup
        created_tables = []

        try:
            # Execute CTAS query SEQUENTIALLY across warehouse sizes
            for warehouse_size in warehouse_sizes:
                warehouse_id = warehouse_id_map[warehouse_size]
                table_name = f"{CATALOG}.{SCHEMA}.BENCHMARK_CTAS_{self.run_id}"
                created_tables.append(table_name)

                logger.info(
                    f"\n[{warehouse_size.upper()}] Starting CTAS benchmark on warehouse {warehouse_id}"
                )

                # Record wall clock start time for this warehouse
                self.storage.record_run_start(
                    run_id=self.run_id,
                    platform="databricks",
                    scenario=scenario,
                    warehouse_size=warehouse_size.upper(),
                    warehouse_name=warehouse_id,
                )

                # Connect to warehouse
                self.connect(warehouse_id=warehouse_id)

                try:
                    # Load the CTAS query
                    ctas_query = self.query_executor.load_ctas_query()

                    # Execute single CTAS query
                    self.query_executor.execute_ctas_query(
                        query_num=0,  # Special marker for CTAS query
                        run_num=1,
                        warehouse_id=warehouse_id,
                        warehouse_size=warehouse_size.upper(),
                        scenario=scenario,
                        query_sql=ctas_query,
                        table_name=table_name,
                    )

                    logger.info(
                        f"\n[{warehouse_size.upper()}] ✅ Completed CTAS benchmark on {warehouse_id}"
                    )

                finally:
                    self.disconnect()

                    # Record wall clock end time for this warehouse
                    self.storage.record_run_end(
                        run_id=self.run_id,
                        platform="databricks",
                        scenario=scenario,
                        warehouse_size=warehouse_size.upper(),
                    )

        finally:
            # Destroy warehouses FIRST (ends timing)
            self.warehouse_manager.destroy_all_warehouses()

            # Drop tables AFTER warehouses destroyed (NOT counted in metrics)
            self._cleanup_ctas_tables(created_tables)

        logger.info("\n" + "=" * 70)
        logger.info("CTAS BENCHMARK COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Results saved to: {DUCKDB_PATH}")
        logger.info(f"Run ID: {self.run_id}")

    def _cleanup_ctas_tables(self, table_names: list[str]):
        """
        Drop CTAS tables created during benchmark.

        This runs AFTER warehouse destruction and is NOT counted in metrics.
        Uses admin warehouse from config for cleanup.

        Args:
            table_names: List of fully-qualified table names to drop
        """
        from common.connections import DatabricksConnection
        from .config import WAREHOUSES

        if not table_names:
            return

        logger.info("\n🧹 Cleaning up CTAS tables (not counted in metrics)...")

        # Connect to admin warehouse for cleanup
        admin_warehouse_id = WAREHOUSES["admin"]

        # Create new connection for cleanup
        cleanup_connection = DatabricksConnection(
            host=DATABRICKS_HOST,
            token=DATABRICKS_TOKEN,
            warehouse_id=admin_warehouse_id,
            catalog=CATALOG,
            schema=SCHEMA,
        )

        try:
            cleanup_connection.connect()
            cursor = cleanup_connection.connection.cursor()

            for table_name in table_names:
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                    logger.info(f"   Dropped: {table_name}")
                except Exception as e:
                    logger.warning(f"   Failed to drop {table_name}: {e}")

            cursor.close()

        finally:
            cleanup_connection.disconnect()

        logger.info("✅ Table cleanup complete")

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
            warehouse_sizes: List of warehouse sizes to test (default: small only)
            query_nums: List of query numbers to run (default: all 1-22)
            num_runs: Number of runs per query (default: 4)
            parallel: If True, run warehouses in parallel (default: True)
        """
        scenario = "normal"

        # Default to small warehouse only (use --warehouse flag for multiple sizes)
        if warehouse_sizes is None:
            warehouse_sizes = ["small"]
        if query_nums is None:
            query_nums = list(range(1, NUM_QUERIES + 1))

        logger.info("=" * 70)
        logger.info("DATABRICKS TPC-H BENCHMARK")
        logger.info("=" * 70)
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"Scenario: {scenario}")
        logger.info(f"Scale Factor: SF{self.scale_factor} (~{self.scale_factor}GB)")
        logger.info(f"Warehouses: {', '.join(warehouse_sizes)}")
        logger.info(f"Queries: {len(query_nums)} queries")
        logger.info(f"Runs per query: {num_runs}")
        logger.info(f"Warehouse execution: {'Parallel' if parallel else 'Sequential'}")
        logger.info("Query execution: Sequential (one query at a time per warehouse)")
        logger.info(
            f"Total query executions: {len(warehouse_sizes) * len(query_nums) * num_runs}"
        )
        logger.info("=" * 70)

        # Initialize warehouse manager
        self.warehouse_manager = WarehouseManager(run_id=self.run_id)

        # Create all warehouses upfront with scenario in name
        warehouse_id_map = self.warehouse_manager.create_all_warehouses(
            warehouse_sizes, scenario
        )

        try:
            if not parallel:
                # Sequential execution
                for warehouse_size in warehouse_sizes:
                    warehouse_id = warehouse_id_map[warehouse_size]
                    # Connect for this warehouse
                    self.connect(warehouse_id=warehouse_id)
                    try:
                        self.run_warehouse_benchmark(
                            warehouse_size, warehouse_id, query_nums, num_runs, scenario
                        )
                    finally:
                        self.disconnect()
            else:
                # Parallel execution across warehouses
                logger.info("\n🚀 Launching parallel execution across all warehouses...")

                # Create separate benchmark instances for each warehouse
                # Each needs its own connection but shares the same run_id
                benchmark_instances = {}
                for warehouse_size in warehouse_sizes:
                    instance = DatabricksBenchmark(
                        scale_factor=self.scale_factor,
                        run_id=self.run_id,  # Share the same run_id
                    )
                    # Share warehouse manager
                    instance.warehouse_manager = self.warehouse_manager
                    benchmark_instances[warehouse_size] = instance

                try:
                    # Connect all instances
                    for warehouse_size, instance in benchmark_instances.items():
                        warehouse_id = warehouse_id_map[warehouse_size]
                        instance.connect(warehouse_id=warehouse_id)

                    # Use ThreadPoolExecutor to run warehouses in parallel
                    with ThreadPoolExecutor(
                        max_workers=len(warehouse_sizes)
                    ) as executor:
                        # Submit all warehouse benchmarks
                        future_to_warehouse = {
                            executor.submit(
                                instance.run_warehouse_benchmark,
                                warehouse_size,
                                warehouse_id_map[warehouse_size],
                                query_nums,
                                num_runs,
                                scenario,
                            ): warehouse_size
                            for warehouse_size, instance in benchmark_instances.items()
                        }

                        # Wait for completion and collect results
                        for future in as_completed(future_to_warehouse):
                            warehouse_size = future_to_warehouse[future]
                            try:
                                future.result()
                            except Exception as e:
                                logger.error(
                                    f"\n❌ Exception in {warehouse_size} warehouse: {e}"
                                )

                finally:
                    # Disconnect all instances BEFORE warehouse cleanup
                    logger.info("\n🔌 Closing all connections...")
                    for instance in benchmark_instances.values():
                        instance.disconnect()

                    # Add a small delay to ensure connections are fully closed
                    time.sleep(3)

        finally:
            # Always clean up warehouses (after connections are closed)
            self.warehouse_manager.destroy_all_warehouses()

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
        choices=WAREHOUSE_SIZES,
        action="append",
        help="Warehouse size(s) to test (can specify multiple times). Default: small",
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
        help="Run warehouses sequentially instead of in parallel. Queries always run sequentially within each warehouse (default: parallel warehouses)",
    )
    parser.add_argument(
        "--scale-factor",
        type=int,
        default=SCALE_FACTOR,
        help=f"TPC-H scale factor (default: {SCALE_FACTOR}). Common values: 100 (100GB), 1000 (1TB), 10000 (10TB)",
    )
    parser.add_argument(
        "--scenario",
        choices=["normal", "coldstart"],
        default="normal",
        help="Scenario to run (default: normal)",
    )

    args = parser.parse_args()

    # Parse query numbers
    query_nums = None
    if args.queries:
        query_nums = [int(q.strip()) for q in args.queries.split(",")]

    # Create benchmark instance
    benchmark = DatabricksBenchmark(scale_factor=args.scale_factor)

    try:
        if args.scenario == "coldstart":
            # Run cold start trial
            benchmark.run_cold_start_trial(
                warehouse_sizes=args.warehouse, query_nums=query_nums
            )
        else:
            # Run normal benchmark
            benchmark.run_benchmark(
                warehouse_sizes=args.warehouse,
                query_nums=query_nums,
                num_runs=args.runs,
                parallel=not args.sequential,
            )
    finally:
        # Disconnect if connected
        if benchmark.conn:
            benchmark.disconnect()


if __name__ == "__main__":
    main()
