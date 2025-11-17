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

from common.logging_config import get_logger

logger = get_logger(__name__)


def run_benchmark(
    warehouse_sizes_snow: Optional[List[str]] = None,
    warehouse_sizes_dbx: Optional[List[str]] = None,
    query_nums: Optional[List[int]] = None,
):
    """
    Run benchmark: Execute queries on Snowflake first, then Databricks.

    Args:
        warehouse_sizes_snow: Snowflake warehouse sizes (default: ["medium"])
        warehouse_sizes_dbx: Databricks warehouse sizes (default: ["small"])
        query_nums: Query numbers to run (default: all 1-22)
    """
    logger.info("🚀 Starting Benchmark")
    logger.info("=" * 80)

    # Import benchmark classes
    from snowflake.benchmark import SnowflakeBenchmark
    from databricks.benchmark import DatabricksBenchmark

    # Run Snowflake first
    logger.info("\n❄️  Running Snowflake benchmark...")
    try:
        sf_benchmark = SnowflakeBenchmark()
        sf_benchmark.run_benchmark(
            warehouse_sizes=warehouse_sizes_snow,
            query_nums=query_nums,
            num_runs=1,
            parallel=False,  # Run sequentially within Snowflake
        )
        logger.info("✅ Snowflake benchmark completed")
    except Exception as e:
        logger.error(f"❌ Snowflake benchmark failed: {e}", exc_info=True)
        raise

    # Run Databricks second
    logger.info("\n🧱 Running Databricks benchmark...")
    try:
        dbx_benchmark = DatabricksBenchmark()
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
  # Run benchmark with default medium size
  python main.py

  # Run with large warehouse (xlarge for Snowflake, large for Databricks)
  python main.py --warehouse-size large

  # Run with specific queries
  python main.py --queries 1,2,3 --warehouse-size large
  python main.py --queries 1-5 --warehouse-size medium
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
        except Exception as e:
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
        # Run benchmark (Snowflake first, then Databricks)
        run_benchmark(
            warehouse_sizes_snow=warehouse_sizes_snow,
            warehouse_sizes_dbx=warehouse_sizes_dbx,
            query_nums=query_nums
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
