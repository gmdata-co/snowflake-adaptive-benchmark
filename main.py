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
        storage.record_run_start(run_id, "snowflake", "normal")
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
        finally:
            storage.record_run_end(run_id, "snowflake", "normal")

    # Run Databricks second
    if run_databricks:
        logger.info("\n🧱 Running Databricks benchmark...")
        storage.record_run_start(run_id, "databricks", "normal")
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
        finally:
            storage.record_run_end(run_id, "databricks", "normal")

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
        storage.record_run_start(run_id, "snowflake", "coldstart")
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
        finally:
            storage.record_run_end(run_id, "snowflake", "coldstart")

    # Run Databricks cold start trial
    if run_databricks:
        logger.info("\n🧱 Running Databricks cold start trial...")
        storage.record_run_start(run_id, "databricks", "coldstart")
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
        finally:
            storage.record_run_end(run_id, "databricks", "coldstart")

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
        storage.record_run_start(run_id, "snowflake", "concurrent")
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
        finally:
            storage.record_run_end(run_id, "snowflake", "concurrent")

    # Run Databricks concurrent benchmark
    if run_databricks:
        logger.info("\n🧱 Running Databricks concurrent benchmark...")
        storage.record_run_start(run_id, "databricks", "concurrent")
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
        finally:
            storage.record_run_end(run_id, "databricks", "concurrent")

    logger.info("\n" + "=" * 80)
    logger.info("✅ All concurrent benchmarks completed")
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

    # SCENARIO 1: Normal Benchmark
    logger.info("\n" + "=" * 80)
    logger.info("SCENARIO 1: NORMAL BENCHMARK")
    logger.info("=" * 80)

    if run_snowflake:
        logger.info("\n❄️  Running Snowflake normal benchmark...")
        storage.record_run_start(run_id, "snowflake", "normal")
        try:
            sf_benchmark = SnowflakeBenchmark(run_id=run_id)
            sf_benchmark.connect()
            sf_benchmark.run_benchmark(
                warehouse_sizes=warehouse_sizes_snow,
                query_nums=query_nums,
                num_runs=1,
                parallel=False,
            )
            sf_benchmark.disconnect()
            logger.info("✅ Snowflake normal benchmark completed")
        except Exception as e:
            logger.error(f"❌ Snowflake normal benchmark failed: {e}", exc_info=True)
            raise
        finally:
            storage.record_run_end(run_id, "snowflake", "normal")

    if run_databricks:
        logger.info("\n🧱 Running Databricks normal benchmark...")
        storage.record_run_start(run_id, "databricks", "normal")
        try:
            dbx_benchmark = DatabricksBenchmark(run_id=run_id)
            dbx_benchmark.run_benchmark(
                warehouse_sizes=warehouse_sizes_dbx,
                query_nums=query_nums,
                num_runs=1,
                parallel=False,
            )
            logger.info("✅ Databricks normal benchmark completed")
        except Exception as e:
            logger.error(f"❌ Databricks normal benchmark failed: {e}", exc_info=True)
            raise
        finally:
            storage.record_run_end(run_id, "databricks", "normal")

    # SCENARIO 2: Cold Start Trial
    logger.info("\n" + "=" * 80)
    logger.info("SCENARIO 2: COLD START TRIAL")
    logger.info("=" * 80)

    # For cold start, use specific queries if not provided
    cold_start_queries = query_nums if query_nums else [1, 3, 5, 10, 18]

    if run_snowflake:
        logger.info("\n❄️  Running Snowflake cold start trial...")
        storage.record_run_start(run_id, "snowflake", "coldstart")
        try:
            sf_benchmark = SnowflakeBenchmark(run_id=run_id)  # SAME run_id!
            sf_benchmark.connect()
            sf_benchmark.run_cold_start_trial(
                warehouse_sizes=warehouse_sizes_snow,
                query_nums=cold_start_queries,
            )
            sf_benchmark.disconnect()
            logger.info("✅ Snowflake cold start trial completed")
        except Exception as e:
            logger.error(f"❌ Snowflake cold start trial failed: {e}", exc_info=True)
            raise
        finally:
            storage.record_run_end(run_id, "snowflake", "coldstart")

    if run_databricks:
        logger.info("\n🧱 Running Databricks cold start trial...")
        storage.record_run_start(run_id, "databricks", "coldstart")
        try:
            dbx_benchmark = DatabricksBenchmark(run_id=run_id)  # SAME run_id!
            dbx_benchmark.run_cold_start_trial(
                warehouse_sizes=warehouse_sizes_dbx,
                query_nums=cold_start_queries,
            )
            logger.info("✅ Databricks cold start trial completed")
        except Exception as e:
            logger.error(f"❌ Databricks cold start trial failed: {e}", exc_info=True)
            raise
        finally:
            storage.record_run_end(run_id, "databricks", "coldstart")

    # SCENARIO 3: Concurrent Benchmark
    logger.info("\n" + "=" * 80)
    logger.info("SCENARIO 3: CONCURRENT BENCHMARK")
    logger.info("=" * 80)

    if run_snowflake:
        logger.info("\n❄️  Running Snowflake concurrent benchmark...")
        storage.record_run_start(run_id, "snowflake", "concurrent")
        try:
            sf_benchmark = SnowflakeBenchmark(run_id=run_id)  # SAME run_id!
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
        finally:
            storage.record_run_end(run_id, "snowflake", "concurrent")

    if run_databricks:
        logger.info("\n🧱 Running Databricks concurrent benchmark...")
        storage.record_run_start(run_id, "databricks", "concurrent")
        try:
            dbx_benchmark = DatabricksBenchmark(run_id=run_id)  # SAME run_id!
            dbx_benchmark.run_concurrent_benchmark(
                warehouse_sizes=warehouse_sizes_dbx,
                query_nums=query_nums,
            )
            logger.info("✅ Databricks concurrent benchmark completed")
        except Exception as e:
            logger.error(f"❌ Databricks concurrent benchmark failed: {e}", exc_info=True)
            raise
        finally:
            storage.record_run_end(run_id, "databricks", "concurrent")

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
  # Run normal benchmark with default medium size
  python main.py

  # Run with large warehouse (xlarge for Snowflake, large for Databricks)
  python main.py --warehouse-size large

  # Run with specific queries
  python main.py --queries 1,2,3 --warehouse-size large
  python main.py --queries 1-5 --warehouse-size medium

  # Run ALL scenarios with unified run ID (normal + cold start + concurrent)
  python main.py --scenario all

  # Run cold start trial only
  python main.py --scenario coldstart

  # Run concurrent benchmark only
  python main.py --scenario concurrent

  # Run cold start trial with specific queries
  python main.py --scenario coldstart --queries 1,5,10

  # Run only Databricks (skip Snowflake)
  python main.py --databricks-only

  # Run only Snowflake (skip Databricks)
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
        choices=["small", "medium", "large"],
        help="Warehouse size to use (automatically maps: small→small/xsmall, medium→medium/small, large→xlarge/large)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        choices=["normal", "coldstart", "concurrent", "all"],
        default="all",
        help="Scenario to run: normal, coldstart, concurrent, or all (default - runs all scenarios with same run_id)",
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

    logger.info("=" * 80)
    logger.info("🚀 Snowflake vs Databricks TPC-H Benchmark")
    logger.info("=" * 80)

    # Map warehouse size to platform-specific sizes
    # The mapping ensures equivalent compute power across platforms
    warehouse_size_mapping = {
        "small": {
            "snowflake": "small",
            "databricks": "xsmall",
        },
        "medium": {
            "snowflake": "medium",
            "databricks": "small",
        },
        "large": {
            "snowflake": "xlarge",
            "databricks": "large",
        },
    }

    # Determine warehouse sizes based on command-line argument or defaults
    if args.warehouse_size:
        size_key = args.warehouse_size
        warehouse_sizes_snow = [warehouse_size_mapping[size_key]["snowflake"]]
        warehouse_sizes_dbx = [warehouse_size_mapping[size_key]["databricks"]]
        logger.info(f"Using warehouse size: {size_key}")
        logger.info(f"  → Snowflake: {warehouse_sizes_snow[0]}")
        logger.info(f"  → Databricks: {warehouse_sizes_dbx[0]}")
    else:
        # Default warehouse sizes: medium for Snowflake, small for Databricks (equivalent)
        warehouse_sizes_snow = ["medium"]
        warehouse_sizes_dbx = ["small"]

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
