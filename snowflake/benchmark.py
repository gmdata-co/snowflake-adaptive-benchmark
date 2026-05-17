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
    DEFAULT_QTM,
    DML_TABLE,
    resolve_idle_policy,
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
        warehouse_type: str = "gen1",
        qtm: Optional[int] = None,
    ):
        """Initialize benchmark runner.

        Args:
            connection_name: Name of connection from ~/.snowflake/connections.toml
            scale_factor: TPC-H scale factor (e.g., 100, 1000)
            run_id: Optional run ID to use (for parallel instances or unified scenarios)
            warehouse_type: "gen1" or "adaptive" — controls CREATE WAREHOUSE syntax.
            qtm: QUERY_THROUGHPUT_MULTIPLIER for adaptive warehouses (ignored for gen1).
        """
        self.connection_name = connection_name
        self.scale_factor = scale_factor
        self.warehouse_type = warehouse_type
        # Normalize: adaptive defaults to DEFAULT_QTM; gen1 always None.
        if warehouse_type == "adaptive":
            self.qtm = qtm if qtm is not None else DEFAULT_QTM
        else:
            self.qtm = None

        # Use SnowflakeConnection abstraction
        self.sf_connection = SnowflakeConnection(
            connection_name=connection_name,
            role=SNOWFLAKE_ROLE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
        )
        self.conn: Optional[snowflake.connector.SnowflakeConnection] = None

        # Idle/shutdown policy for this whole run, resolved once from
        # warehouse_type + BENCHMARK_IMMEDIATE_DROP. Recorded as a real column
        # on every result + run_metadata row so the dashboard toggle is driven
        # by ground truth, not post-hoc run_id guessing.
        self.idle_policy = resolve_idle_policy(warehouse_type)

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

    def _run_start(self, *args, **kwargs):
        """record_run_start with this run's idle_policy injected."""
        kwargs.setdefault("idle_policy", self.idle_policy)
        return getattr(self.storage, "record_run_start")(*args, **kwargs)

    def _run_end(self, *args, **kwargs):
        """record_run_end with this run's idle_policy injected."""
        kwargs.setdefault("idle_policy", self.idle_policy)
        return getattr(self.storage, "record_run_end")(*args, **kwargs)

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
        self._run_start(
            run_id=self.run_id,
            platform="snowflake",
            scenario=scenario,
            warehouse_size=warehouse_size.upper(),
            warehouse_name=warehouse_name,
            warehouse_type=self.warehouse_type,
            qtm=self.qtm,
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
                        warehouse_type=self.warehouse_type,
                        qtm=self.qtm,
                    )

            logger.info(
                f"\n[{warehouse_size.upper()}] ✅ Completed all queries on {warehouse_name}"
            )

        except Exception as e:
            logger.error(f"\n[{warehouse_size.upper()}] ❌ Error: {e}")
            raise
        finally:
            # Record wall clock end time for this warehouse
            self._run_end(
                run_id=self.run_id,
                platform="snowflake",
                scenario=scenario,
                warehouse_size=warehouse_size.upper(),
                warehouse_type=self.warehouse_type,
                qtm=self.qtm,
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
                self._run_start(
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
                    self._run_end(
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

        For gen1, scales the warehouse with multi-cluster (MIN=1, MAX=4) and STANDARD
        scaling policy. For adaptive, the QTM (set on the SnowflakeBenchmark instance)
        controls concurrent throughput — multi-cluster does not apply.

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
        logger.info(f"Warehouse type: {self.warehouse_type}")
        if self.warehouse_type == "adaptive":
            logger.info(f"QTM: {self.qtm}")
        logger.info(f"Scale Factor: SF{self.scale_factor} (~{self.scale_factor}GB)")
        logger.info(f"Warehouses: {', '.join(warehouse_sizes)}")
        logger.info(f"Queries: {query_nums} ({len(query_nums)} queries)")
        logger.info("Execution: All queries in parallel (concurrent)")

        # Multi-cluster only applies to gen1. Adaptive's QTM handles concurrency.
        if self.warehouse_type == "gen1":
            max_clusters = min(len(query_nums), 4)
            min_clusters = 1
            logger.info(
                f"Warehouse: Multi-cluster gen1 (min: {min_clusters}, max: {max_clusters})"
            )
        else:
            max_clusters = None
            min_clusters = None
            logger.info(f"Warehouse: Adaptive (QTM={self.qtm})")
        logger.info("=" * 70)

        warehouse_map = self.warehouse_manager.create_all_warehouses(
            warehouse_sizes,
            scenario,
            warehouse_type=self.warehouse_type,
            qtm=self.qtm,
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
                self._run_start(
                    run_id=self.run_id,
                    platform="snowflake",
                    scenario=scenario,
                    warehouse_size=warehouse_size.upper(),
                    warehouse_name=warehouse_name,
                    warehouse_type=self.warehouse_type,
                    qtm=self.qtm,
                )

                # Create separate benchmark instances for each query
                # Each needs its own connection for concurrent execution
                benchmark_instances = []
                for _ in query_nums:
                    instance = SnowflakeBenchmark(
                        connection_name=self.connection_name,
                        scale_factor=self.scale_factor,
                        run_id=self.run_id,  # Share the same run_id
                        warehouse_type=self.warehouse_type,
                        qtm=self.qtm,
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
                    self._run_end(
                        run_id=self.run_id,
                        platform="snowflake",
                        scenario=scenario,
                        warehouse_size=warehouse_size.upper(),
                        warehouse_type=self.warehouse_type,
                        qtm=self.qtm,
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
        """Execute a single query (helper for concurrent execution)."""
        # Switch to the warehouse
        instance.warehouse_manager.switch_warehouse(warehouse_name)

        # Execute the query once (run_num=1)
        instance.query_executor.execute_query(
            query_num=query_num,
            run_num=1,
            warehouse_name=warehouse_name,
            warehouse_size=warehouse_size.upper(),
            scenario=scenario,
            warehouse_type=instance.warehouse_type,
            qtm=instance.qtm,
        )

    def run_ctas_benchmark(
        self,
        warehouse_sizes: list[str] = None,
        variants: list[str] = None,
    ):
        """
        Run CTAS benchmark: Execute multiple CTAS query variants.

        Executes 5 variants: narrow_tall, standard_tall, medium_wide,
        very_wide, filtered. Each creates a table with different data shapes.

        Args:
            warehouse_sizes: List of warehouse sizes to test (default: ["medium"])
            variants: List of variants to run (default: all 5)
        """
        scenario = "ctas"

        if warehouse_sizes is None:
            warehouse_sizes = ["medium"]

        if variants is None:
            variants = ["narrow_tall", "standard_tall", "medium_wide",
                       "very_wide", "filtered"]

        logger.info("=" * 70)
        logger.info("SNOWFLAKE CTAS BENCHMARK")
        logger.info("=" * 70)
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"Scenario: {scenario}")
        logger.info(f"Scale Factor: SF{self.scale_factor} (~{self.scale_factor}GB)")
        logger.info(f"Warehouses: {', '.join(warehouse_sizes)}")
        logger.info(f"Variants: {', '.join(variants)}")
        logger.info("Execution: Sequential (CREATE TABLE AS SELECT)")
        logger.info("=" * 70)

        # Create warehouses with scenario in name
        warehouse_map = self.warehouse_manager.create_all_warehouses(
            warehouse_sizes, scenario
        )

        # Track created tables for cleanup
        created_tables = []

        try:
            # Execute CTAS variants SEQUENTIALLY across warehouse sizes
            for warehouse_size in warehouse_sizes:
                warehouse_name = warehouse_map[warehouse_size]

                logger.info(
                    f"\n[{warehouse_size.upper()}] Starting CTAS benchmark on {warehouse_name}"
                )

                # Record wall clock start time for this warehouse
                self._run_start(
                    run_id=self.run_id,
                    platform="snowflake",
                    scenario=scenario,
                    warehouse_size=warehouse_size.upper(),
                    warehouse_name=warehouse_name,
                )

                try:
                    # Switch to this warehouse
                    self.warehouse_manager.switch_warehouse(warehouse_name)

                    # Execute ALL variants sequentially on this warehouse
                    for variant in variants:
                        logger.info(f"\n  [{warehouse_size.upper()}] Executing variant: {variant}")

                        # Load variant query
                        variant_query = self.query_executor.load_ctas_query_variant(variant)

                        # Generate unique table name for this variant
                        table_name = f"BENCHMARK_CTAS_{variant.upper()}_{self.run_id}"
                        created_tables.append(table_name)

                        # Execute variant
                        self.query_executor.execute_ctas_query(
                            query_num=0,  # Special marker for CTAS query
                            run_num=1,
                            warehouse_name=warehouse_name,
                            warehouse_size=warehouse_size.upper(),
                            scenario=scenario,
                            query_sql=variant_query,
                            table_name=table_name,
                            ctas_variant=variant,
                        )

                    logger.info(
                        f"\n[{warehouse_size.upper()}] ✅ Completed all variants on {warehouse_name}"
                    )

                finally:
                    # Record wall clock end time for this warehouse
                    self._run_end(
                        run_id=self.run_id,
                        platform="snowflake",
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

        Args:
            table_names: List of table names to drop
        """
        if not table_names:
            return

        logger.info("\n🧹 Cleaning up CTAS tables (not counted in metrics)...")

        # Snowflake: No warehouse needed for DROP TABLE (serverless operation)
        cursor = self.conn.cursor()

        for table_name in table_names:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                logger.info(f"   Dropped: {table_name}")
            except Exception as e:
                logger.warning(f"   Failed to drop {table_name}: {e}")

        cursor.close()
        logger.info("✅ Table cleanup complete")

    def _setup_dml_table(self):
        """
        Set up the DML target table by dropping and recreating from source.

        Note: SNOWFLAKE_SAMPLE_DATA tables are from a data share and cannot be cloned.
        We use CTAS instead with a dedicated LARGE setup warehouse.
        This runs BEFORE benchmark timing starts (not counted in metrics).
        """
        logger.info("\n🔧 Setting up DML target table (not counted in metrics)...")

        # Create a dedicated LARGE warehouse for setup (6B rows needs horsepower)
        setup_warehouse_name = f"BENCHMARK_WH_SETUP_{self.run_id}"
        logger.info(f"   Creating LARGE setup warehouse: {setup_warehouse_name}")

        cursor = self.conn.cursor()

        try:
            # Need SYSADMIN role to create warehouse
            cursor.execute("USE ROLE SYSADMIN")

            # Create large warehouse for setup
            cursor.execute(f"""
                CREATE WAREHOUSE IF NOT EXISTS {setup_warehouse_name}
                WITH WAREHOUSE_SIZE = 'LARGE'
                AUTO_SUSPEND = 60
                AUTO_RESUME = TRUE
                INITIALLY_SUSPENDED = FALSE
            """)

            # Switch back to benchmark role for data operations
            cursor.execute(f"USE ROLE {SNOWFLAKE_ROLE}")
            cursor.execute(f"USE WAREHOUSE {setup_warehouse_name}")
            logger.info(f"   Using setup warehouse: {setup_warehouse_name}")

            # Ensure the target database + schema exist (env-driven, not hardcoded).
            # DML_TABLE looks like "<DB>.<SCHEMA>.LINEITEM_DML".
            db_name, schema_name, _ = DML_TABLE.split(".")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {db_name}.{schema_name}")
            logger.info(f"   Ensured {db_name}.{schema_name} exists")

            # Drop existing table to ensure clean state
            cursor.execute(f"DROP TABLE IF EXISTS {DML_TABLE}")
            logger.info(f"   Dropped existing {DML_TABLE} (if any)")

            # CTAS from source - can't use CLONE because source is from a data share
            logger.info(f"   Creating {DML_TABLE} via CTAS from SF{self.scale_factor} (this may take several minutes)...")
            cursor.execute(f"""
                CREATE TABLE {DML_TABLE} AS
                SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF{self.scale_factor}.LINEITEM
            """)
            logger.info(f"   Created fresh {DML_TABLE} from source")

        except Exception as e:
            logger.error(f"   Failed to set up DML table: {e}")
            raise
        finally:
            # Always destroy the setup warehouse (need SYSADMIN)
            try:
                cursor.execute("USE ROLE SYSADMIN")
                cursor.execute(f"DROP WAREHOUSE IF EXISTS {setup_warehouse_name}")
                logger.info(f"   Destroyed setup warehouse: {setup_warehouse_name}")
                cursor.execute(f"USE ROLE {SNOWFLAKE_ROLE}")
            except Exception as e:
                logger.warning(f"   Failed to destroy setup warehouse: {e}")
            cursor.close()

        logger.info("✅ DML table setup complete")

    def run_dml_benchmark(
        self,
        warehouse_sizes: list[str] = None,
    ):
        """
        Run DML benchmark: Execute DELETE + INSERT operations on lineitem data.

        Measures partition refresh performance by:
        1. Deleting a monthly slice of data (June 1995, ~75M rows at SF1000)
        2. Re-inserting the same data from source

        Args:
            warehouse_sizes: List of warehouse sizes to test (default: ["medium"])
        """
        scenario = "dml"
        operations = ["delete", "insert"]

        if warehouse_sizes is None:
            warehouse_sizes = ["medium"]

        logger.info("=" * 70)
        logger.info("SNOWFLAKE DML BENCHMARK")
        logger.info("=" * 70)
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"Scenario: {scenario}")
        logger.info(f"Warehouse type: {self.warehouse_type}")
        if self.warehouse_type == "adaptive":
            logger.info(f"QTM: {self.qtm}")
        logger.info(f"Scale Factor: SF{self.scale_factor} (~{self.scale_factor}GB)")
        logger.info(f"Warehouses: {', '.join(warehouse_sizes)}")
        logger.info(f"Operations: {', '.join(operations)}")
        logger.info("Target: June 1995 lineitem data (~1.25% of table)")
        logger.info("=" * 70)

        # Setup: Create fresh target table BEFORE benchmark (not counted in metrics)
        # Uses a dedicated LARGE warehouse that gets destroyed after setup
        self._setup_dml_table()

        # Create benchmark warehouses with scenario in name
        warehouse_map = self.warehouse_manager.create_all_warehouses(
            warehouse_sizes,
            scenario,
            warehouse_type=self.warehouse_type,
            qtm=self.qtm,
        )

        try:
            # Execute DML operations for each warehouse size
            for warehouse_size in warehouse_sizes:
                warehouse_name = warehouse_map[warehouse_size]

                logger.info(
                    f"\n[{warehouse_size.upper()}] Starting DML benchmark on {warehouse_name}"
                )

                # Record wall clock start time for this warehouse
                self._run_start(
                    run_id=self.run_id,
                    platform="snowflake",
                    scenario=scenario,
                    warehouse_size=warehouse_size.upper(),
                    warehouse_name=warehouse_name,
                    warehouse_type=self.warehouse_type,
                    qtm=self.qtm,
                )

                try:
                    # Switch to this warehouse
                    self.warehouse_manager.switch_warehouse(warehouse_name)

                    # Execute DELETE and INSERT sequentially
                    for operation in operations:
                        logger.info(f"\n  [{warehouse_size.upper()}] Executing: {operation.upper()}")

                        # Execute DML operation and record metrics
                        self.query_executor.execute_dml_query(
                            operation=operation,
                            run_num=1,
                            warehouse_name=warehouse_name,
                            warehouse_size=warehouse_size.upper(),
                            scenario=scenario,
                            warehouse_type=self.warehouse_type,
                            qtm=self.qtm,
                        )

                    logger.info(
                        f"\n[{warehouse_size.upper()}] ✅ Completed DML operations on {warehouse_name}"
                    )

                finally:
                    # Record wall clock end time for this warehouse
                    self._run_end(
                        run_id=self.run_id,
                        platform="snowflake",
                        scenario=scenario,
                        warehouse_size=warehouse_size.upper(),
                        warehouse_type=self.warehouse_type,
                        qtm=self.qtm,
                    )

        finally:
            # Always clean up warehouses
            self.warehouse_manager.destroy_all_warehouses()

        logger.info("\n" + "=" * 70)
        logger.info("DML BENCHMARK COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Results saved to: {DUCKDB_PATH}")
        logger.info(f"Run ID: {self.run_id}")

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
        scenario = "sequential"

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
        logger.info(f"Warehouse type: {self.warehouse_type}")
        if self.warehouse_type == "adaptive":
            logger.info(f"QTM: {self.qtm}")
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
            warehouse_sizes,
            scenario,
            warehouse_type=self.warehouse_type,
            qtm=self.qtm,
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
                        warehouse_type=self.warehouse_type,
                        qtm=self.qtm,
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
        logger.info("1. Wait ~90 minutes for ACCOUNT_USAGE to populate")
        logger.info("2. Run: uv run snowflake/enrich_results.py")
        logger.info("3. Run: uv run common/transformations/run_transformations.py")
        logger.info("4. Query results: SELECT * FROM run_summary_agg;")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Snowflake TPC-H Benchmark")
    parser.add_argument(
        "--warehouse",
        choices=["small", "medium", "large", "xlarge"],
        action="append",
        help="Warehouse size(s) to test (can specify multiple times). Default: medium",
    )
    parser.add_argument(
        "--warehouse-type",
        choices=["gen1", "adaptive"],
        default="gen1",
        help="Warehouse generation: 'gen1' (pins GENERATION='1') or 'adaptive' "
             "(CREATE ADAPTIVE WAREHOUSE with QTM). Default: gen1.",
    )
    parser.add_argument(
        "--qtm",
        type=int,
        default=DEFAULT_QTM,
        help=f"QUERY_THROUGHPUT_MULTIPLIER for adaptive warehouses "
             f"(default: {DEFAULT_QTM}). Ignored when --warehouse-type=gen1.",
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
        help="Run warehouses sequentially instead of in parallel.",
    )
    parser.add_argument(
        "--scale-factor",
        type=int,
        default=SCALE_FACTOR,
        help=f"TPC-H scale factor (default: {SCALE_FACTOR}). SF100 = ~600M LINEITEM rows.",
    )
    parser.add_argument(
        "--scenario",
        choices=["sequential", "concurrent", "dml"],
        default="sequential",
        help="Scenario to run (default: sequential)",
    )

    args = parser.parse_args()

    # Parse query numbers
    query_nums = None
    if args.queries:
        query_nums = [int(q.strip()) for q in args.queries.split(",")]

    # Create benchmark instance
    benchmark = SnowflakeBenchmark(
        connection_name=args.connection,
        scale_factor=args.scale_factor,
        warehouse_type=args.warehouse_type,
        qtm=args.qtm,
    )

    # Connect
    benchmark.connect()

    try:
        if args.scenario == "concurrent":
            benchmark.run_concurrent_benchmark(
                warehouse_sizes=args.warehouse, query_nums=query_nums
            )
        elif args.scenario == "dml":
            benchmark.run_dml_benchmark(warehouse_sizes=args.warehouse)
        else:
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
