#!/usr/bin/env python3
"""
Main Orchestrator for Snowflake vs Databricks TPC-H Benchmark

Runs three types of benchmarks:
1. Sequential: Run all queries once, one after another
2. Concurrent: Submit all queries at once to test queue processing
3. Cold Start: Test cold warehouse performance on queries 1-5
"""

import argparse
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List
import os

# Add project root to path for common imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from common.logging_config import get_logger

logger = get_logger(__name__)


def run_sequential_benchmark(
    warehouse_sizes_snow: Optional[List[str]] = None,
    warehouse_sizes_dbx: Optional[List[str]] = None,
    query_nums: Optional[List[int]] = None,
):
    """
    Run sequential benchmark: Execute all queries once, one after another.

    Both Snowflake and Databricks benchmarks run concurrently (in parallel threads),
    but within each platform, queries execute sequentially.

    Args:
        warehouse_sizes_snow: Snowflake warehouse sizes (default: ["small", "medium", "xlarge"])
        warehouse_sizes_dbx: Databricks warehouse sizes (default: ["xsmall", "small", "large"])
        query_nums: Query numbers to run (default: all 1-22)
    """
    logger.info("🚀 Starting Sequential Benchmark")
    logger.info("=" * 80)

    # Build command arguments
    query_arg = []
    if query_nums:
        query_arg = ["--queries", ",".join(map(str, query_nums))]

    def run_snowflake():
        """Run Snowflake sequential benchmark"""
        logger.info("❄️  Initializing Snowflake benchmark...")

        cmd = [
            "uv", "run", "python", "benchmark.py",
            "--runs", "1",
            "--sequential",
        ]
        if warehouse_sizes_snow:
            for wh in warehouse_sizes_snow:
                cmd.extend(["--warehouse", wh])
        cmd.extend(query_arg)

        result = subprocess.run(
            cmd,
            cwd=project_root / "snowflake",
            capture_output=False,  # Let output stream to console
            text=True
        )

        if result.returncode == 0:
            logger.info("✅ Snowflake sequential benchmark completed")
        else:
            raise Exception(f"Snowflake benchmark failed with exit code {result.returncode}")
        return "snowflake"

    def run_databricks():
        """Run Databricks sequential benchmark"""
        logger.info("🧱 Initializing Databricks benchmark...")

        # Source ~/.zshrc for databricks credentials as per CLAUDE.md
        source_cmd = "source ~/.zshrc && "

        cmd = [
            "uv", "run", "python", "benchmark.py",
            "--runs", "1",
            "--sequential",
        ]
        if warehouse_sizes_dbx:
            for wh in warehouse_sizes_dbx:
                cmd.extend(["--warehouse", wh])
        cmd.extend(query_arg)

        # Run with sourced environment
        full_cmd = source_cmd + " ".join(cmd)
        result = subprocess.run(
            full_cmd,
            cwd=project_root / "databricks",
            capture_output=False,  # Let output stream to console
            text=True,
            shell=True,
            executable="/bin/zsh"
        )

        if result.returncode == 0:
            logger.info("✅ Databricks sequential benchmark completed")
        else:
            raise Exception(f"Databricks benchmark failed with exit code {result.returncode}")
        return "databricks"

    # Run both platforms concurrently using ThreadPoolExecutor
    logger.info("🔄 Running Snowflake and Databricks benchmarks concurrently...")
    logger.info("   (Queries within each platform run sequentially)")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(run_snowflake): "snowflake",
            executor.submit(run_databricks): "databricks",
        }

        for future in as_completed(futures):
            platform = futures[future]
            try:
                result = future.result()
                logger.info(f"✅ {platform.capitalize()} thread completed successfully")
            except Exception as e:
                logger.error(f"❌ {platform.capitalize()} benchmark failed: {e}", exc_info=True)

    logger.info("=" * 80)
    logger.info("✅ Sequential Benchmark completed")


def run_concurrent_benchmark(
    warehouse_sizes_snow: Optional[List[str]] = None,
    warehouse_sizes_dbx: Optional[List[str]] = None,
    query_nums: Optional[List[int]] = None,
):
    """
    Run concurrent benchmark: Submit all queries at once to test queue processing.

    This will test how well Snowflake and Databricks handle concurrent query loads.
    All queries are submitted simultaneously, and the warehouse processes them
    according to its queuing and concurrency capabilities.

    Implementation Plan:
    - Use ThreadPoolExecutor with max_workers = number of queries
    - Submit all queries to the warehouse at once
    - Measure queue time, execution time, and total time
    - Compare how each platform handles query queuing and prioritization

    Args:
        warehouse_sizes_snow: Snowflake warehouse sizes to test
        warehouse_sizes_dbx: Databricks warehouse sizes to test
        query_nums: Query numbers to run concurrently (default: all 1-22)

    Note: This is a placeholder for future implementation.
    """
    logger.info("🚧 Concurrent Benchmark - Not yet implemented")
    logger.info("   This will submit all queries simultaneously to test queue processing")
    pass


def run_cold_start_benchmark(
    query_nums: Optional[List[int]] = None,
):
    """
    Run cold start benchmark: Test warehouse cold start performance.

    Measures the performance impact of starting a warehouse from a completely
    cold state. Typically runs queries 1-5 to get a representative sample.

    Implementation Plan:
    - For Snowflake: Create a fresh warehouse for each run
    - For Databricks: Use stop_start_warehouses=True to force cold starts
    - Measure warehouse startup time separately from query execution time
    - Compare cold vs warm performance characteristics
    - Track time to first byte and total execution time

    Args:
        query_nums: Query numbers to run (default: 1-5 for cold start testing)

    Note: This is a placeholder for future implementation.
    """
    logger.info("❄️  Cold Start Benchmark - Not yet implemented")
    logger.info("   This will test performance on completely cold warehouses (queries 1-5)")
    pass


def main():
    """
    Main entry point for the benchmark orchestrator.

    Parses command-line arguments and runs the requested benchmark scenarios.
    """
    parser = argparse.ArgumentParser(
        description="Snowflake vs Databricks TPC-H Benchmark Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all benchmarks (default)
  python main.py

  # Run only sequential benchmark
  python main.py --sequential

  # Run concurrent benchmark when implemented
  python main.py --concurrent

  # Run cold start benchmark when implemented
  python main.py --cold-start

  # Run specific combinations
  python main.py --sequential --cold-start

  # Run with specific queries
  python main.py --sequential --queries 1,2,3
  python main.py --sequential --queries 1-5
        """,
    )

    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run sequential benchmark (queries run one after another)",
    )
    parser.add_argument(
        "--concurrent",
        action="store_true",
        help="Run concurrent benchmark (all queries submitted at once)",
    )
    parser.add_argument(
        "--cold-start",
        action="store_true",
        help="Run cold start benchmark (queries 1-5 on cold warehouses)",
    )
    parser.add_argument(
        "--queries",
        type=str,
        help="Comma-separated query numbers to run (e.g., '1,2,3' or '1-5')",
    )

    args = parser.parse_args()

    # If no specific benchmark is selected, run all
    run_all = not (args.sequential or args.concurrent or args.cold_start)

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
        except Exception as e:
            logger.error(f"Invalid query format: {args.queries}")
            sys.exit(1)

    logger.info("=" * 80)
    logger.info("🚀 Snowflake vs Databricks TPC-H Benchmark")
    logger.info("=" * 80)

    # Default warehouse sizes: medium for Snowflake, small for Databricks (equivalent)
    warehouse_sizes_snow = ["medium"]
    warehouse_sizes_dbx = ["small"]

    try:
        # Run sequential benchmark
        if args.sequential or run_all:
            run_sequential_benchmark(
                warehouse_sizes_snow=warehouse_sizes_snow,
                warehouse_sizes_dbx=warehouse_sizes_dbx,
                query_nums=query_nums
            )
            logger.info("")

        # Run concurrent benchmark
        if args.concurrent or run_all:
            run_concurrent_benchmark(
                warehouse_sizes_snow=warehouse_sizes_snow,
                warehouse_sizes_dbx=warehouse_sizes_dbx,
                query_nums=query_nums
            )
            logger.info("")

        # Run cold start benchmark
        if args.cold_start or run_all:
            run_cold_start_benchmark(query_nums=query_nums)
            logger.info("")

        logger.info("=" * 80)
        logger.info("✅ All requested benchmarks completed")
        logger.info("=" * 80)
        logger.info("📊 Results stored in: benchmark_results.duckdb")
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
