#!/usr/bin/env python3
"""
Snowflake TPC-H Benchmark Runner

Executes TPC-H queries against Snowflake and logs performance metrics.
"""

from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import sys

# Add parent directory to path to import from common
sys.path.insert(0, str(Path(__file__).parent.parent))

import snowflake.connector
from common.connections import SnowflakeConnection
from common.storage import BenchmarkStorage
from common.logging_config import get_logger
from .config import (
    SNOWFLAKE_CONNECTION,
    SNOWFLAKE_ROLE,
    SNOWFLAKE_DATABASE,
    SNOWFLAKE_SCHEMA,
    NUM_RUNS,
    NUM_QUERIES,
    SCALE_FACTOR,
    DUCKDB_PATH,
)
from .warehouse_manager import WarehouseManager
from .query_executor import QueryExecutor

logger = get_logger(__name__)

# Global storage instance for thread-safe DuckDB writes
storage = BenchmarkStorage(DUCKDB_PATH)


class SnowflakeBenchmark:
    """Manages Snowflake TPC-H benchmark execution."""

    def __init__(
        self,
        connection_name: str = SNOWFLAKE_CONNECTION,
        scale_factor: int = SCALE_FACTOR,
        run_id: str = None,
    ):
        """Initialize benchmark runner.

        Args:
            connection_name: Name of connection from ~/.snowflake/connections.toml
            scale_factor: TPC-H scale factor (e.g., 100, 1000)
            run_id: Optional run ID to use (for parallel instances or unified scenarios)
        """
        self.connection_name = connection_name
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

        # Managers (initialized when connected)
        self.warehouse_manager: Optional[WarehouseManager] = None
        self.query_executor: Optional[QueryExecutor] = None

    def _get_next_run_id(self) -> str:
        """
        Get the next sequential run ID by reading existing DuckDB data.

        Returns:
            Zero-padded 3-digit run ID (e.g., "001", "002", "003")
        """
        return self.storage.get_next_run_id()

    def connect(self):
        """Establish connection to Snowflake and initialize managers."""
        # Use SnowflakeConnection abstraction
        self.sf_connection.connect()

        # Store reference to the underlying connection
        self.conn = self.sf_connection.connection

        # Initialize managers
        self.warehouse_manager = WarehouseManager(
            connection=self.conn, run_id=self.run_id
        )
        self.query_executor = QueryExecutor(
            connection=self.conn,
            storage=self.storage,
            run_id=self.run_id,
            scale_factor=self.scale_factor,
        )

    def disconnect(self):
        """Close Snowflake connection."""
        if self.sf_connection:
            self.sf_connection.disconnect()
            self.conn = None
            self.warehouse_manager = None
            self.query_executor = None

    def run_warehouse_benchmark(
        self,
        warehouse_size: str,
        warehouse_name: str,
        query_nums: list[int],
        num_runs: int,
        scenario: str = "normal",
    ):
        """
        Run benchmark for a single warehouse size.

        This method is designed to run in a separate thread for parallel execution.

        Args:
            warehouse_size: Warehouse size key (e.g., "small", "medium", "xlarge")
            warehouse_name: Name of the warehouse to use
            query_nums: List of query numbers to run
            num_runs: Number of runs per query
            scenario: Scenario name (e.g., "normal", "coldstart", "concurrent")
        """
        logger.info(
            f"\n[{warehouse_size.upper()}] Starting benchmark on {warehouse_name}"
        )
        logger.info(f"[{warehouse_size.upper()}] Using warehouse: {warehouse_name}")

        # Record wall clock start time for this warehouse
        self.storage.record_run_start(
            run_id=self.run_id,
            platform="snowflake",
            scenario=scenario,
            warehouse_size=warehouse_size.upper(),
            warehouse_name=warehouse_name,
        )

        try:
            # Switch to this warehouse
            self.warehouse_manager.switch_warehouse(warehouse_name)

            # Execute all queries
            for query_num in query_nums:
                for run_num in range(1, num_runs + 1):
                    # Execute query (run_type is determined automatically)
                    self.query_executor.execute_query(
                        query_num=query_num,
                        run_num=run_num,
                        warehouse_name=warehouse_name,
                        warehouse_size=warehouse_size.upper(),
                        scenario=scenario,
                    )

            logger.info(
                f"\n[{warehouse_size.upper()}] ✅ Completed all queries on {warehouse_name}"
            )

        except Exception as e:
            logger.error(f"\n[{warehouse_size.upper()}] ❌ Error: {e}")
            raise
        finally:
            # Record wall clock end time for this warehouse
            self.storage.record_run_end(
                run_id=self.run_id,
                platform="snowflake",
                scenario=scenario,
                warehouse_size=warehouse_size.upper(),
            )

    def run_cold_start_trial(
        self,
        warehouse_sizes: list[str] = None,
        query_nums: list[int] = None,
    ):
        """
        Run cold start trial: suspend warehouse between each query execution.

        This measures true cold start performance by suspending the warehouse
        after each query, forcing it to start from a completely cold state
        for the next query.

        Args:
            warehouse_sizes: List of warehouse sizes to test (default: ["medium"])
            query_nums: List of query numbers to run (default: [1, 3, 5, 10, 18])
        """
        scenario = "coldstart"

        if warehouse_sizes is None:
            warehouse_sizes = ["medium"]
        if query_nums is None:
            query_nums = [1, 3, 5, 10, 18]

        logger.info("=" * 70)
        logger.info("SNOWFLAKE COLD START TRIAL")
        logger.info("=" * 70)
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"Scenario: {scenario}")
        logger.info(f"Scale Factor: SF{self.scale_factor} (~{self.scale_factor}GB)")
        logger.info(f"Warehouses: {', '.join(warehouse_sizes)}")
        logger.info(f"Queries: {query_nums}")
        logger.info("=" * 70)

        # Create warehouses with scenario in name
        warehouse_map = self.warehouse_manager.create_all_warehouses(
            warehouse_sizes, scenario
        )

        try:
            # Execute each query with suspend/resume cycle for each warehouse
            for warehouse_size in warehouse_sizes:
                warehouse_name = warehouse_map[warehouse_size]

                logger.info(
                    f"\n[{warehouse_size.upper()}] Starting COLD START trial on {warehouse_name}"
                )
                logger.info(f"[{warehouse_size.upper()}] Queries: {query_nums}")

                # Record wall clock start time for this warehouse
                self.storage.record_run_start(
                    run_id=self.run_id,
                    platform="snowflake",
                    scenario=scenario,
                    warehouse_size=warehouse_size.upper(),
                    warehouse_name=warehouse_name,
                )

                try:
                    # Switch to this warehouse
                    self.warehouse_manager.switch_warehouse(warehouse_name)

                    for query_num in query_nums:
                        # Resume warehouse before query
                        logger.info(
                            f"\n[{warehouse_size.upper()}] Resuming warehouse for query {query_num}"
                        )
                        self.warehouse_manager.resume_warehouse(warehouse_name)

                        # Execute query once (run_num=1, always cold start)
                        self.query_executor.execute_query(
                            query_num=query_num,
                            run_num=1,
                            warehouse_name=warehouse_name,
                            warehouse_size=warehouse_size.upper(),
                            scenario=scenario,
                            force_run_type="cold",  # Force cold run type
                        )

                        # Suspend warehouse after query
                        logger.info(
                            f"[{warehouse_size.upper()}] Suspending warehouse after query {query_num}"
                        )
                        self.warehouse_manager.suspend_warehouse(warehouse_name)

                    logger.info(
                        f"\n[{warehouse_size.upper()}] ✅ Completed COLD START trial on {warehouse_name}"
                    )
                finally:
                    # Record wall clock end time for this warehouse
                    self.storage.record_run_end(
                        run_id=self.run_id,
                        platform="snowflake",
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
            warehouse_sizes: List of warehouse sizes to test (default: ["medium"])
            query_nums: List of query numbers to run (default: all 1-22)
        """
        scenario = "concurrent"

        if warehouse_sizes is None:
            warehouse_sizes = ["medium"]
        if query_nums is None:
            query_nums = list(range(1, NUM_QUERIES + 1))

        logger.info("=" * 70)
        logger.info("SNOWFLAKE CONCURRENT BENCHMARK")
        logger.info("=" * 70)
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"Scenario: {scenario}")
        logger.info(f"Scale Factor: SF{self.scale_factor} (~{self.scale_factor}GB)")
        logger.info(f"Warehouses: {', '.join(warehouse_sizes)}")
        logger.info(f"Queries: {query_nums} ({len(query_nums)} queries)")
        logger.info("Execution: All queries in parallel (concurrent)")

        # Multi-cluster warehouse config for concurrent execution
        # Scale up to handle parallel query load (Enterprise Edition required)
        max_clusters = min(len(query_nums), 4)  # Cap at 4 clusters max
        min_clusters = 1  # Start with 1, scale up as needed
        logger.info(f"Warehouse: Multi-cluster (min: {min_clusters}, max: {max_clusters})")
        logger.info("=" * 70)

        # Create multi-cluster warehouses for concurrent testing
        warehouse_map = self.warehouse_manager.create_all_warehouses(
            warehouse_sizes,
            scenario,
            max_cluster_count=max_clusters,
            min_cluster_count=min_clusters,
        )

        try:
            # Execute concurrent queries for each warehouse
            for warehouse_size in warehouse_sizes:
                warehouse_name = warehouse_map[warehouse_size]

                logger.info(
                    f"\n[{warehouse_size.upper()}] Starting CONCURRENT benchmark on {warehouse_name}"
                )
                logger.info(
                    f"[{warehouse_size.upper()}] Executing {len(query_nums)} queries in parallel"
                )

                # Record wall clock start time for this warehouse
                self.storage.record_run_start(
                    run_id=self.run_id,
                    platform="snowflake",
                    scenario=scenario,
                    warehouse_size=warehouse_size.upper(),
                    warehouse_name=warehouse_name,
                )

                # Create separate benchmark instances for each query
                # Each needs its own connection for concurrent execution
                benchmark_instances = []
                for _ in query_nums:
                    instance = SnowflakeBenchmark(
                        connection_name=self.connection_name,
                        scale_factor=self.scale_factor,
                        run_id=self.run_id,  # Share the same run_id
                    )
                    benchmark_instances.append(instance)

                try:
                    # Connect all instances
                    for instance in benchmark_instances:
                        instance.connect()
                        # Share the created warehouses list
                        instance.warehouse_manager.created_warehouses = (
                            self.warehouse_manager.created_warehouses
                        )

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
                                warehouse_name,
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
                    for instance in benchmark_instances:
                        instance.disconnect()
                    # Record wall clock end time for this warehouse
                    self.storage.record_run_end(
                        run_id=self.run_id,
                        platform="snowflake",
                        scenario=scenario,
                        warehouse_size=warehouse_size.upper(),
                    )

                logger.info(
                    f"\n[{warehouse_size.upper()}] ✅ Completed CONCURRENT benchmark on {warehouse_name}"
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
        instance: "SnowflakeBenchmark",
        query_num: int,
        warehouse_name: str,
        warehouse_size: str,
        scenario: str,
    ):
        """
        Execute a single query (helper for concurrent execution).

        Args:
            instance: SnowflakeBenchmark instance with its own connection
            query_num: Query number to execute
            warehouse_name: Name of the warehouse to use
            warehouse_size: Warehouse size key
            scenario: Scenario name
        """
        # Switch to the warehouse
        instance.warehouse_manager.switch_warehouse(warehouse_name)

        # Execute the query once (run_num=1)
        instance.query_executor.execute_query(
            query_num=query_num,
            run_num=1,
            warehouse_name=warehouse_name,
            warehouse_size=warehouse_size.upper(),
            scenario=scenario,
        )

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
            warehouse_sizes: List of warehouse sizes to test (default: medium only)
            query_nums: List of query numbers to run (default: all 1-22)
            num_runs: Number of runs per query (default: 4)
            parallel: If True, run warehouses in parallel (default: True)
        """
        scenario = "normal"

        # Default to medium warehouse only (use --warehouse flag for multiple sizes)
        if warehouse_sizes is None:
            warehouse_sizes = ["medium"]
        if query_nums is None:
            query_nums = list(range(1, NUM_QUERIES + 1))

        logger.info("=" * 70)
        logger.info("SNOWFLAKE TPC-H BENCHMARK")
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

        # Create warehouses with scenario in name
        warehouse_map = self.warehouse_manager.create_all_warehouses(
            warehouse_sizes, scenario
        )

        try:
            if not parallel:
                # Sequential execution
                for warehouse_size in warehouse_sizes:
                    warehouse_name = warehouse_map[warehouse_size]
                    self.run_warehouse_benchmark(
                        warehouse_size, warehouse_name, query_nums, num_runs, scenario
                    )
            else:
                # Parallel execution across warehouses
                if len(warehouse_sizes) > 1:
                    logger.info(
                        "\n🚀 Launching parallel execution across all warehouses..."
                    )
                else:
                    logger.info(
                        f"\n🚀 Starting benchmark on {warehouse_sizes[0]} warehouse..."
                    )

                # Create separate benchmark instances for each warehouse
                # Each needs its own connection but shares the same run_id
                benchmark_instances = {}
                for warehouse_size in warehouse_sizes:
                    instance = SnowflakeBenchmark(
                        connection_name=self.connection_name,
                        scale_factor=self.scale_factor,
                        run_id=self.run_id,  # Share the same run_id
                    )
                    # Share warehouse manager's created list for cleanup
                    benchmark_instances[warehouse_size] = instance

                try:
                    # Connect all instances
                    for warehouse_size, instance in benchmark_instances.items():
                        instance.connect()
                        # Share the created warehouses list
                        instance.warehouse_manager.created_warehouses = (
                            self.warehouse_manager.created_warehouses
                        )

                    # Use ThreadPoolExecutor to run warehouses in parallel
                    with ThreadPoolExecutor(max_workers=len(warehouse_sizes)) as executor:
                        # Submit all warehouse benchmarks
                        future_to_warehouse = {
                            executor.submit(
                                instance.run_warehouse_benchmark,
                                warehouse_size,
                                warehouse_map[warehouse_size],
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
                    # Disconnect all instances
                    for instance in benchmark_instances.values():
                        instance.disconnect()

        finally:
            # Always clean up warehouses
            self.warehouse_manager.destroy_all_warehouses()

        logger.info("\n" + "=" * 70)
        logger.info("BENCHMARK COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Results saved to: {DUCKDB_PATH}")
        logger.info(f"Run ID: {self.run_id}")
        logger.info("\nNext steps:")
        logger.info("1. Wait 45 minutes for ACCOUNT_USAGE to populate")
        logger.info("2. Run: uv run snowflake/enrich_results.py")
        logger.info("3. Run: uv run common/transformations/run_transformations.py")
        logger.info("4. Query results: SELECT * FROM platform_comparison;")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Snowflake TPC-H Benchmark")
    parser.add_argument(
        "--warehouse",
        choices=["small", "medium", "xlarge"],
        action="append",
        help="Warehouse size(s) to test (can specify multiple times). Default: medium",
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
        help="Run warehouses sequentially instead of in parallel. Queries always run sequentially within each warehouse (default: parallel warehouses)",
    )
    parser.add_argument(
        "--scale-factor",
        type=int,
        default=SCALE_FACTOR,
        help=f"TPC-H scale factor (default: {SCALE_FACTOR}). Common values: 1000 (1TB), 10000 (10TB)",
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
    benchmark = SnowflakeBenchmark(
        connection_name=args.connection, scale_factor=args.scale_factor
    )

    # Connect
    benchmark.connect()

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
        benchmark.disconnect()


if __name__ == "__main__":
    main()
