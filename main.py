#!/usr/bin/env python3
"""
Main Orchestrator for Snowflake vs Databricks TPC-H Benchmark

Runs benchmarks sequentially: Snowflake first, then Databricks.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, List

# Add project root to path for common imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from common.logging_config import get_logger  # noqa: E402
from common.storage import BenchmarkStorage  # noqa: E402

logger = get_logger(__name__)

# Path to DuckDB database (same as used in benchmark modules)
DUCKDB_PATH = project_root / "benchmark_results.duckdb"


def run_benchmark(
    warehouse_sizes_snow: Optional[List[str]] = None,
    warehouse_sizes_dbx: Optional[List[str]] = None,
    query_nums: Optional[List[int]] = None,
    run_snowflake: bool = True,
    run_databricks: bool = True,
):
    """
    Run benchmark: Execute queries on Snowflake first, then Databricks.

    Args:
        warehouse_sizes_snow: Snowflake warehouse sizes (default: ["medium"])
        warehouse_sizes_dbx: Databricks warehouse sizes (default: ["small"])
        query_nums: Query numbers to run (default: all 1-22)
        run_snowflake: Whether to run Snowflake benchmark (default: True)
        run_databricks: Whether to run Databricks benchmark (default: True)
    """
    logger.info("🚀 Starting Benchmark")
    logger.info("=" * 80)

    # Generate unified run ID for both platforms
    storage = BenchmarkStorage(DUCKDB_PATH)
    run_id = storage.get_next_run_id()
    logger.info(f"📊 Run ID: {run_id}")
    logger.info("=" * 80)

    # Import benchmark classes
    from snowflake.benchmark import SnowflakeBenchmark
    from databricks.benchmark import DatabricksBenchmark

    # Run Snowflake first
    if run_snowflake:
        logger.info("\n❄️  Running Snowflake benchmark...")
        try:
            sf_benchmark = SnowflakeBenchmark(run_id=run_id)
            sf_benchmark.connect()
            sf_benchmark.run_benchmark(
                warehouse_sizes=warehouse_sizes_snow,
                query_nums=query_nums,
                num_runs=1,
                parallel=False,  # Run sequentially within Snowflake
            )
            sf_benchmark.disconnect()
            logger.info("✅ Snowflake benchmark completed")
        except Exception as e:
            logger.error(f"❌ Snowflake benchmark failed: {e}", exc_info=True)
            raise

    # Run Databricks second
    if run_databricks:
        logger.info("\n🧱 Running Databricks benchmark...")
        try:
            dbx_benchmark = DatabricksBenchmark(run_id=run_id)
            dbx_benchmark.run_benchmark(
                warehouse_sizes=warehouse_sizes_dbx,
                query_nums=query_nums,
                num_runs=1,
                parallel=False,  # Run sequentially within Databricks
            )
            logger.info("✅ Databricks benchmark completed")
        except Exception as e:
            logger.error(f"❌ Databricks benchmark failed: {e}", exc_info=True)
            raise

    logger.info("\n" + "=" * 80)
    logger.info("✅ All benchmarks completed")
    logger.info("=" * 80)


def run_cold_start_trial(
    warehouse_sizes_snow: Optional[List[str]] = None,
    warehouse_sizes_dbx: Optional[List[str]] = None,
    query_nums: Optional[List[int]] = None,
    run_snowflake: bool = True,
    run_databricks: bool = True,
):
    """
    Run cold start trial: Suspend/stop warehouse between each query execution.

    This measures true cold start performance by suspending (Snowflake) or
    stopping (Databricks) the warehouse after each query.

    Args:
        warehouse_sizes_snow: Snowflake warehouse sizes (default: ["medium"])
        warehouse_sizes_dbx: Databricks warehouse sizes (default: ["small"])
        query_nums: Query numbers to run (default: [1, 3, 5, 10, 18])
        run_snowflake: Whether to run Snowflake trial (default: True)
        run_databricks: Whether to run Databricks trial (default: True)
    """
    logger.info("🚀 Starting Cold Start Trial")
    logger.info("=" * 80)

    if query_nums is None:
        query_nums = [1, 3, 5, 10, 18]

    # Generate unified run ID for both platforms
    storage = BenchmarkStorage(DUCKDB_PATH)
    run_id = storage.get_next_run_id()
    logger.info(f"📊 Run ID: {run_id}")
    logger.info("=" * 80)

    # Import benchmark classes
    from snowflake.benchmark import SnowflakeBenchmark
    from databricks.benchmark import DatabricksBenchmark

    # Run Snowflake cold start trial
    if run_snowflake:
        logger.info("\n❄️  Running Snowflake cold start trial...")
        try:
            sf_benchmark = SnowflakeBenchmark(run_id=run_id)
            sf_benchmark.connect()
            sf_benchmark.run_cold_start_trial(
                warehouse_sizes=warehouse_sizes_snow,
                query_nums=query_nums,
            )
            sf_benchmark.disconnect()
            logger.info("✅ Snowflake cold start trial completed")
        except Exception as e:
            logger.error(f"❌ Snowflake cold start trial failed: {e}", exc_info=True)
            raise

    # Run Databricks cold start trial
    if run_databricks:
        logger.info("\n🧱 Running Databricks cold start trial...")
        try:
            dbx_benchmark = DatabricksBenchmark(run_id=run_id)
            dbx_benchmark.run_cold_start_trial(
                warehouse_sizes=warehouse_sizes_dbx,
                query_nums=query_nums,
            )
            logger.info("✅ Databricks cold start trial completed")
        except Exception as e:
            logger.error(f"❌ Databricks cold start trial failed: {e}", exc_info=True)
            raise

    logger.info("\n" + "=" * 80)
    logger.info("✅ All cold start trials completed")
    logger.info("=" * 80)


def run_concurrent_scenario(
    warehouse_sizes_snow: Optional[List[str]] = None,
    warehouse_sizes_dbx: Optional[List[str]] = None,
    query_nums: Optional[List[int]] = None,
    run_snowflake: bool = True,
    run_databricks: bool = True,
):
    """
    Run concurrent scenario: Execute all queries in parallel on the same warehouse.

    This measures performance under concurrent load by executing all queries
    simultaneously using a multi-cluster warehouse.

    Args:
        warehouse_sizes_snow: Snowflake warehouse sizes (default: ["medium"])
        warehouse_sizes_dbx: Databricks warehouse sizes (default: ["small"])
        query_nums: Query numbers to run (default: all 1-22)
        run_snowflake: Whether to run Snowflake trial (default: True)
        run_databricks: Whether to run Databricks trial (default: True)
    """
    logger.info("🚀 Starting Concurrent Benchmark")
    logger.info("=" * 80)

    # Generate unified run ID for both platforms
    storage = BenchmarkStorage(DUCKDB_PATH)
    run_id = storage.get_next_run_id()
    logger.info(f"📊 Run ID: {run_id}")
    logger.info("=" * 80)

    # Import benchmark classes
    from snowflake.benchmark import SnowflakeBenchmark
    from databricks.benchmark import DatabricksBenchmark

    # Run Snowflake concurrent benchmark
    if run_snowflake:
        logger.info("\n❄️  Running Snowflake concurrent benchmark...")
        try:
            sf_benchmark = SnowflakeBenchmark(run_id=run_id)
            sf_benchmark.connect()
            sf_benchmark.run_concurrent_benchmark(
                warehouse_sizes=warehouse_sizes_snow,
                query_nums=query_nums,
            )
            sf_benchmark.disconnect()
            logger.info("✅ Snowflake concurrent benchmark completed")
        except Exception as e:
            logger.error(f"❌ Snowflake concurrent benchmark failed: {e}", exc_info=True)
            raise

    # Run Databricks concurrent benchmark
    if run_databricks:
        logger.info("\n🧱 Running Databricks concurrent benchmark...")
        try:
            dbx_benchmark = DatabricksBenchmark(run_id=run_id)
            dbx_benchmark.run_concurrent_benchmark(
                warehouse_sizes=warehouse_sizes_dbx,
                query_nums=query_nums,
            )
            logger.info("✅ Databricks concurrent benchmark completed")
        except Exception as e:
            logger.error(f"❌ Databricks concurrent benchmark failed: {e}", exc_info=True)
            raise

    logger.info("\n" + "=" * 80)
    logger.info("✅ All concurrent benchmarks completed")
    logger.info("=" * 80)


def run_ctas_scenario(
    warehouse_sizes_snow: Optional[List[str]] = None,
    warehouse_sizes_dbx: Optional[List[str]] = None,
    variants: Optional[List[str]] = None,
    run_snowflake: bool = True,
    run_databricks: bool = True,
):
    """
    Run CTAS scenario: Execute CTAS query variants.

    This creates tables with different data shapes to benchmark write performance.

    Args:
        warehouse_sizes_snow: Snowflake warehouse sizes (default: ["medium"])
        warehouse_sizes_dbx: Databricks warehouse sizes (default: ["small"])
        variants: CTAS variants to run (default: all 5)
        run_snowflake: Whether to run Snowflake (default: True)
        run_databricks: Whether to run Databricks (default: True)
    """
    logger.info("🚀 Starting CTAS Benchmark")
    logger.info("=" * 80)

    # Generate unified run ID for both platforms
    storage = BenchmarkStorage(DUCKDB_PATH)
    run_id = storage.get_next_run_id()
    logger.info(f"📊 Run ID: {run_id}")
    logger.info("=" * 80)

    # Import benchmark classes
    from snowflake.benchmark import SnowflakeBenchmark
    from databricks.benchmark import DatabricksBenchmark

    # Run Snowflake CTAS
    if run_snowflake:
        logger.info("\n❄️  Running Snowflake CTAS benchmark...")
        try:
            sf_benchmark = SnowflakeBenchmark(run_id=run_id)
            sf_benchmark.connect()
            sf_benchmark.run_ctas_benchmark(
                warehouse_sizes=warehouse_sizes_snow,
                variants=variants,
            )
            sf_benchmark.disconnect()
            logger.info("✅ Snowflake CTAS benchmark completed")
        except Exception as e:
            logger.error(f"❌ Snowflake CTAS benchmark failed: {e}", exc_info=True)
            raise

    # Run Databricks CTAS
    if run_databricks:
        logger.info("\n🧱 Running Databricks CTAS benchmark...")
        try:
            dbx_benchmark = DatabricksBenchmark(run_id=run_id)
            dbx_benchmark.run_ctas_benchmark(
                warehouse_sizes=warehouse_sizes_dbx,
                variants=variants,
            )
            logger.info("✅ Databricks CTAS benchmark completed")
        except Exception as e:
            logger.error(f"❌ Databricks CTAS benchmark failed: {e}", exc_info=True)
            raise

    logger.info("\n" + "=" * 80)
    logger.info("✅ All CTAS benchmarks completed")
    logger.info("=" * 80)


def run_all_scenarios(
    warehouse_sizes_snow: Optional[List[str]] = None,
    warehouse_sizes_dbx: Optional[List[str]] = None,
    query_nums: Optional[List[int]] = None,
    run_snowflake: bool = True,
    run_databricks: bool = True,
):
    """
    Run ALL scenarios with a single shared run_id for comparison.

    Runs all Snowflake benchmarks first (all sizes, all scenarios), then all Databricks.
    Warehouse lifecycle is per-size: create when size begins, destroy when size ends.

    Args:
        warehouse_sizes_snow: Snowflake warehouse sizes (default: ["medium"])
        warehouse_sizes_dbx: Databricks warehouse sizes (default: ["small"])
        query_nums: Query numbers to run (default: all 1-22 for normal, specific for cold start)
        run_snowflake: Whether to run Snowflake (default: True)
        run_databricks: Whether to run Databricks (default: True)
    """
    logger.info("🚀 Running ALL scenarios with unified Run ID")
    logger.info("=" * 80)

    # Generate SINGLE run_id for all scenarios
    storage = BenchmarkStorage(DUCKDB_PATH)
    run_id = storage.get_next_run_id()
    logger.info(f"📊 Unified Run ID: {run_id}")
    logger.info("=" * 80)

    # Import benchmark classes
    from snowflake.benchmark import SnowflakeBenchmark
    from databricks.benchmark import DatabricksBenchmark

    # Default warehouse sizes
    if warehouse_sizes_snow is None:
        warehouse_sizes_snow = ["medium"]
    if warehouse_sizes_dbx is None:
        warehouse_sizes_dbx = ["small"]

    # For cold start, use specific queries if not provided
    cold_start_queries = query_nums if query_nums else [1, 3, 5, 10, 18]

    # =========================================================================
    # SNOWFLAKE: Run all sizes and scenarios first
    # =========================================================================
    if run_snowflake:
        logger.info("\n" + "=" * 80)
        logger.info("❄️  SNOWFLAKE: Running all sizes and scenarios")
        logger.info("=" * 80)

        for snow_size in warehouse_sizes_snow:
            logger.info("\n" + "=" * 80)
            logger.info(f"❄️  SNOWFLAKE - WAREHOUSE SIZE: {snow_size.upper()}")
            logger.info("=" * 80)

            # SCENARIO 1: Normal Benchmark
            logger.info("\n" + "-" * 60)
            logger.info(f"[{snow_size.upper()}] SCENARIO 1: NORMAL BENCHMARK")
            logger.info("-" * 60)

            logger.info(f"\n❄️  Running Snowflake normal benchmark ({snow_size})...")
            try:
                sf_benchmark = SnowflakeBenchmark(run_id=run_id)
                sf_benchmark.connect()
                sf_benchmark.run_benchmark(
                    warehouse_sizes=[snow_size],
                    query_nums=query_nums,
                    num_runs=1,
                    parallel=False,
                )
                sf_benchmark.disconnect()
                logger.info(f"✅ Snowflake normal benchmark ({snow_size}) completed")
            except Exception as e:
                logger.error(f"❌ Snowflake normal benchmark ({snow_size}) failed: {e}", exc_info=True)
                raise

            # SCENARIO 2: Cold Start Trial
            logger.info("\n" + "-" * 60)
            logger.info(f"[{snow_size.upper()}] SCENARIO 2: COLD START TRIAL")
            logger.info("-" * 60)

            logger.info(f"\n❄️  Running Snowflake cold start trial ({snow_size})...")
            try:
                sf_benchmark = SnowflakeBenchmark(run_id=run_id)
                sf_benchmark.connect()
                sf_benchmark.run_cold_start_trial(
                    warehouse_sizes=[snow_size],
                    query_nums=cold_start_queries,
                )
                sf_benchmark.disconnect()
                logger.info(f"✅ Snowflake cold start trial ({snow_size}) completed")
            except Exception as e:
                logger.error(f"❌ Snowflake cold start trial ({snow_size}) failed: {e}", exc_info=True)
                raise

            # SCENARIO 3: Concurrent Benchmark
            logger.info("\n" + "-" * 60)
            logger.info(f"[{snow_size.upper()}] SCENARIO 3: CONCURRENT BENCHMARK")
            logger.info("-" * 60)

            logger.info(f"\n❄️  Running Snowflake concurrent benchmark ({snow_size})...")
            try:
                sf_benchmark = SnowflakeBenchmark(run_id=run_id)
                sf_benchmark.connect()
                sf_benchmark.run_concurrent_benchmark(
                    warehouse_sizes=[snow_size],
                    query_nums=query_nums,
                )
                sf_benchmark.disconnect()
                logger.info(f"✅ Snowflake concurrent benchmark ({snow_size}) completed")
            except Exception as e:
                logger.error(f"❌ Snowflake concurrent benchmark ({snow_size}) failed: {e}", exc_info=True)
                raise

            # SCENARIO 4: CTAS Benchmark
            logger.info("\n" + "-" * 60)
            logger.info(f"[{snow_size.upper()}] SCENARIO 4: CTAS BENCHMARK")
            logger.info("-" * 60)

            logger.info(f"\n❄️  Running Snowflake CTAS benchmark ({snow_size})...")
            try:
                sf_benchmark = SnowflakeBenchmark(run_id=run_id)
                sf_benchmark.connect()
                sf_benchmark.run_ctas_benchmark(
                    warehouse_sizes=[snow_size],
                )
                sf_benchmark.disconnect()
                logger.info(f"✅ Snowflake CTAS benchmark ({snow_size}) completed")
            except Exception as e:
                logger.error(f"❌ Snowflake CTAS benchmark ({snow_size}) failed: {e}", exc_info=True)
                raise

            logger.info(f"\n✅ Snowflake completed all scenarios for {snow_size.upper()}")

        logger.info("\n" + "=" * 80)
        logger.info("✅ SNOWFLAKE: All sizes and scenarios completed")
        logger.info("=" * 80)

    # =========================================================================
    # DATABRICKS: Run all sizes and scenarios second
    # =========================================================================
    if run_databricks:
        logger.info("\n" + "=" * 80)
        logger.info("🧱 DATABRICKS: Running all sizes and scenarios")
        logger.info("=" * 80)

        for dbx_size in warehouse_sizes_dbx:
            logger.info("\n" + "=" * 80)
            logger.info(f"🧱 DATABRICKS - WAREHOUSE SIZE: {dbx_size.upper()}")
            logger.info("=" * 80)

            # SCENARIO 1: Normal Benchmark
            logger.info("\n" + "-" * 60)
            logger.info(f"[{dbx_size.upper()}] SCENARIO 1: NORMAL BENCHMARK")
            logger.info("-" * 60)

            logger.info(f"\n🧱 Running Databricks normal benchmark ({dbx_size})...")
            try:
                dbx_benchmark = DatabricksBenchmark(run_id=run_id)
                dbx_benchmark.run_benchmark(
                    warehouse_sizes=[dbx_size],
                    query_nums=query_nums,
                    num_runs=1,
                    parallel=False,
                )
                logger.info(f"✅ Databricks normal benchmark ({dbx_size}) completed")
            except Exception as e:
                logger.error(f"❌ Databricks normal benchmark ({dbx_size}) failed: {e}", exc_info=True)
                raise

            # SCENARIO 2: Cold Start Trial
            logger.info("\n" + "-" * 60)
            logger.info(f"[{dbx_size.upper()}] SCENARIO 2: COLD START TRIAL")
            logger.info("-" * 60)

            logger.info(f"\n🧱 Running Databricks cold start trial ({dbx_size})...")
            try:
                dbx_benchmark = DatabricksBenchmark(run_id=run_id)
                dbx_benchmark.run_cold_start_trial(
                    warehouse_sizes=[dbx_size],
                    query_nums=cold_start_queries,
                )
                logger.info(f"✅ Databricks cold start trial ({dbx_size}) completed")
            except Exception as e:
                logger.error(f"❌ Databricks cold start trial ({dbx_size}) failed: {e}", exc_info=True)
                raise

            # SCENARIO 3: Concurrent Benchmark
            logger.info("\n" + "-" * 60)
            logger.info(f"[{dbx_size.upper()}] SCENARIO 3: CONCURRENT BENCHMARK")
            logger.info("-" * 60)

            logger.info(f"\n🧱 Running Databricks concurrent benchmark ({dbx_size})...")
            try:
                dbx_benchmark = DatabricksBenchmark(run_id=run_id)
                dbx_benchmark.run_concurrent_benchmark(
                    warehouse_sizes=[dbx_size],
                    query_nums=query_nums,
                )
                logger.info(f"✅ Databricks concurrent benchmark ({dbx_size}) completed")
            except Exception as e:
                logger.error(f"❌ Databricks concurrent benchmark ({dbx_size}) failed: {e}", exc_info=True)
                raise

            # SCENARIO 4: CTAS Benchmark
            logger.info("\n" + "-" * 60)
            logger.info(f"[{dbx_size.upper()}] SCENARIO 4: CTAS BENCHMARK")
            logger.info("-" * 60)

            logger.info(f"\n🧱 Running Databricks CTAS benchmark ({dbx_size})...")
            try:
                dbx_benchmark = DatabricksBenchmark(run_id=run_id)
                dbx_benchmark.run_ctas_benchmark(
                    warehouse_sizes=[dbx_size],
                )
                logger.info(f"✅ Databricks CTAS benchmark ({dbx_size}) completed")
            except Exception as e:
                logger.error(f"❌ Databricks CTAS benchmark ({dbx_size}) failed: {e}", exc_info=True)
                raise

            logger.info(f"\n✅ Databricks completed all scenarios for {dbx_size.upper()}")

        logger.info("\n" + "=" * 80)
        logger.info("✅ DATABRICKS: All sizes and scenarios completed")
        logger.info("=" * 80)

    logger.info("\n" + "=" * 80)
    logger.info(f"✅ All scenarios completed with unified Run ID: {run_id}")
    logger.info("=" * 80)


def main():
    """
    Main entry point for the benchmark orchestrator.

    Parses command-line arguments and runs benchmarks.
    """
    parser = argparse.ArgumentParser(
        description="Snowflake vs Databricks TPC-H Benchmark Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all scenarios with default medium warehouse
  python main.py

  # Run all scenarios with ALL warehouse sizes (medium, large, xl)
  python main.py --warehouse-size all

  # Run with specific warehouse sizes (comma-separated)
  python main.py --warehouse-size medium,xl

  # Run with xl warehouse only
  python main.py --warehouse-size xl

  # Run with specific queries
  python main.py --queries 1,2,3 --warehouse-size xl
  python main.py --queries 1-5 --warehouse-size medium

  # Run ALL scenarios with ALL warehouse sizes
  python main.py --scenario all --warehouse-size all

  # Run cold start trial only
  python main.py --scenario coldstart

  # Run concurrent benchmark only
  python main.py --scenario concurrent

  # Run cold start trial with specific queries
  python main.py --scenario coldstart --queries 1,5,10

  # Run CTAS scenario only
  python main.py --scenario ctas

  # Run CTAS with specific warehouse size
  python main.py --scenario ctas --warehouse-size xl

  # Run only Databricks (skip Snowflake)
  python main.py --databricks-only

  # Run only Snowflake (skip Snowflake)
  python main.py --snowflake-only
        """,
    )

    parser.add_argument(
        "--queries",
        type=str,
        help="Comma-separated query numbers to run (e.g., '1,2,3' or '1-5')",
    )
    parser.add_argument(
        "--warehouse-size",
        type=str,
        default="medium",
        help="Warehouse size(s) to use. Options: small, medium, large, xl, 2xl, all, or comma-separated (e.g., 'medium,xl'). Maps automatically: small→small/small, medium→medium/small, large→large/medium, xl→xlarge/large, 2xl→2xlarge/xlarge. Default: medium",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        choices=["normal", "coldstart", "concurrent", "ctas", "all"],
        default="all",
        help="Scenario to run: normal, coldstart, concurrent, ctas, or all (default - runs all scenarios with same run_id)",
    )
    parser.add_argument(
        "--snowflake-only",
        action="store_true",
        help="Run only Snowflake benchmark/trial (skip Databricks)",
    )
    parser.add_argument(
        "--databricks-only",
        action="store_true",
        help="Run only Databricks benchmark/trial (skip Snowflake)",
    )
    parser.add_argument(
        "--ctas-variants",
        type=str,
        help="Comma-separated CTAS variants to run. Options: narrow_tall, standard_tall, medium_wide, very_wide, filtered. Default: all",
    )

    args = parser.parse_args()

    # Parse query numbers if provided
    query_nums = None
    if args.queries:
        try:
            if "-" in args.queries:
                # Range format: "1-5"
                start, end = args.queries.split("-")
                query_nums = list(range(int(start), int(end) + 1))
            else:
                # Comma-separated: "1,2,3"
                query_nums = [int(q.strip()) for q in args.queries.split(",")]
            logger.info(f"Running queries: {query_nums}")
        except Exception:
            logger.error(f"Invalid query format: {args.queries}")
            sys.exit(1)

    # Parse CTAS variants if provided
    ctas_variants = None
    if args.ctas_variants:
        valid_variants = ["narrow_tall", "standard_tall", "medium_wide", "very_wide", "filtered"]
        ctas_variants = [v.strip() for v in args.ctas_variants.split(",")]
        for v in ctas_variants:
            if v not in valid_variants:
                logger.error(f"Invalid CTAS variant: {v}. Must be one of: {valid_variants}")
                sys.exit(1)
        logger.info(f"Running CTAS variants: {ctas_variants}")

    logger.info("=" * 80)
    logger.info("🚀 Snowflake vs Databricks TPC-H Benchmark")
    logger.info("=" * 80)

    # Map warehouse size to platform-specific sizes
    # The mapping ensures equivalent compute power across platforms
    # Databricks is "minus 1 size" compared to Snowflake
    warehouse_size_mapping = {
        "small": {
            "snowflake": "small",
            "databricks": "small",  # Databricks smallest available
        },
        "medium": {
            "snowflake": "medium",
            "databricks": "small",
        },
        "large": {
            "snowflake": "large",
            "databricks": "medium",
        },
        "xl": {
            "snowflake": "xlarge",
            "databricks": "large",
        },
        "2xl": {
            "snowflake": "2xlarge",
            "databricks": "xlarge",
        },
    }

    # Parse warehouse sizes - supports: single value, "all", or comma-separated
    def parse_warehouse_sizes(size_arg: str) -> list:
        """Parse warehouse size argument into list of size keys."""
        if size_arg == "all":
            return ["small", "medium", "large", "xl", "2xl"]
        sizes = [s.strip() for s in size_arg.split(",")]
        valid_sizes = ["small", "medium", "large", "xl", "2xl"]
        for s in sizes:
            if s not in valid_sizes:
                logger.error(f"Invalid warehouse size: {s}. Must be one of: {valid_sizes}")
                sys.exit(1)
        return sizes

    size_keys = parse_warehouse_sizes(args.warehouse_size)
    warehouse_sizes_snow = [warehouse_size_mapping[k]["snowflake"] for k in size_keys]
    warehouse_sizes_dbx = [warehouse_size_mapping[k]["databricks"] for k in size_keys]

    logger.info(f"Using warehouse size(s): {size_keys}")
    for i, size_key in enumerate(size_keys):
        logger.info(f"  → {size_key}: Snowflake {warehouse_sizes_snow[i]} / Databricks {warehouse_sizes_dbx[i]}")

    try:
        # Determine which platforms to run
        run_snowflake = not args.databricks_only
        run_databricks = not args.snowflake_only

        # Run based on scenario
        if args.scenario == "all":
            logger.info("Running ALL scenarios with unified run ID (normal + cold start + concurrent)")
            run_all_scenarios(
                warehouse_sizes_snow=warehouse_sizes_snow,
                warehouse_sizes_dbx=warehouse_sizes_dbx,
                query_nums=query_nums,
                run_snowflake=run_snowflake,
                run_databricks=run_databricks,
            )
        elif args.scenario == "coldstart":
            logger.info("Running COLD START trial (warehouse suspended between queries)")
            run_cold_start_trial(
                warehouse_sizes_snow=warehouse_sizes_snow,
                warehouse_sizes_dbx=warehouse_sizes_dbx,
                query_nums=query_nums,
                run_snowflake=run_snowflake,
                run_databricks=run_databricks,
            )
        elif args.scenario == "concurrent":
            logger.info("Running CONCURRENT benchmark (all queries in parallel)")
            run_concurrent_scenario(
                warehouse_sizes_snow=warehouse_sizes_snow,
                warehouse_sizes_dbx=warehouse_sizes_dbx,
                query_nums=query_nums,
                run_snowflake=run_snowflake,
                run_databricks=run_databricks,
            )
        elif args.scenario == "ctas":
            logger.info("Running CTAS benchmark (CREATE TABLE AS SELECT)")
            run_ctas_scenario(
                warehouse_sizes_snow=warehouse_sizes_snow,
                warehouse_sizes_dbx=warehouse_sizes_dbx,
                variants=ctas_variants,
                run_snowflake=run_snowflake,
                run_databricks=run_databricks,
            )
        else:  # normal
            # Run benchmark (Snowflake first, then Databricks)
            run_benchmark(
                warehouse_sizes_snow=warehouse_sizes_snow,
                warehouse_sizes_dbx=warehouse_sizes_dbx,
                query_nums=query_nums,
                run_snowflake=run_snowflake,
                run_databricks=run_databricks,
            )

        logger.info("\n📊 Results stored in: benchmark_results.duckdb")
        logger.info("📝 Logs available in:")
        logger.info("   - logs/snowflake.log (Snowflake-specific logs)")
        logger.info("   - logs/databricks.log (Databricks-specific logs)")
        logger.info("   - logs/common.log (Shared/common logs)")

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Benchmark failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
