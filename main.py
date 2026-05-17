#!/usr/bin/env python3
"""
Main Orchestrator for Snowflake Adaptive vs Gen1 Warehouse Benchmark

Runs TPC-H scenarios against Snowflake warehouses of two generations:
- gen1: legacy standard warehouse with GENERATION='1' pinned (Snowflake's new
  default is Gen2 in most regions as of mid-2025, so this must be explicit).
- adaptive: CREATE ADAPTIVE WAREHOUSE with MAX_QUERY_PERFORMANCE_LEVEL +
  QUERY_THROUGHPUT_MULTIPLIER (QTM).

Each (warehouse_type, size, qtm) variant gets its own freshly-created,
uniquely-named warehouse so Snowflake billing records (WAREHOUSE_METERING_HISTORY)
attribute credits cleanly per variant. Never ALTER between variants.
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
from snowflake.config import (  # noqa: E402
    DEFAULT_QTM,
    WAREHOUSE_SIZES,
    WAREHOUSE_TYPES,
    DUCKDB_PATH,
)

logger = get_logger(__name__)

# DUCKDB_PATH comes from config so BENCHMARK_DUCKDB_PATH (per-track isolation)
# stays consistent between main.py's run_id allocation and the benchmark's
# module-global storage instance — they must point at the same file.

VALID_SCENARIOS = ["sequential", "concurrent", "dml"]


def _run_one_scenario(
    sf_benchmark,
    scenario: str,
    warehouse_sizes: List[str],
    query_nums: Optional[List[int]],
    num_runs: int = 1,
):
    """Dispatch a single scenario on an already-connected SnowflakeBenchmark."""
    if scenario == "sequential":
        sf_benchmark.run_benchmark(
            warehouse_sizes=warehouse_sizes,
            query_nums=query_nums,
            num_runs=num_runs,
            parallel=False,
        )
    elif scenario == "concurrent":
        sf_benchmark.run_concurrent_benchmark(
            warehouse_sizes=warehouse_sizes,
            query_nums=query_nums,
        )
    elif scenario == "dml":
        sf_benchmark.run_dml_benchmark(warehouse_sizes=warehouse_sizes)
    else:
        raise ValueError(f"Unknown scenario: {scenario}")


def run_experiment(
    warehouse_types: List[str],
    warehouse_sizes: List[str],
    scenarios: List[str],
    qtm: int,
    query_nums: Optional[List[int]] = None,
    num_runs: int = 1,
):
    """
    Run a benchmark experiment across (warehouse_type, scenario, sizes).

    For each warehouse_type in `warehouse_types`, runs each scenario in `scenarios`
    across all `warehouse_sizes`. QTM applies only when warehouse_type='adaptive'.

    All runs share one run_id so they appear together in result aggregations.
    """
    logger.info("=" * 80)
    logger.info("🚀 Snowflake Adaptive vs Gen1 TPC-H Benchmark")
    logger.info("=" * 80)

    storage = BenchmarkStorage(DUCKDB_PATH)
    run_id = storage.get_next_run_id()
    logger.info(f"📊 Run ID: {run_id}")
    logger.info(f"Warehouse types: {warehouse_types}")
    logger.info(f"Sizes:           {warehouse_sizes}")
    logger.info(f"Scenarios:       {scenarios}")
    logger.info(f"QTM (adaptive):  {qtm}")
    logger.info("=" * 80)

    from snowflake.benchmark import SnowflakeBenchmark  # local import to honor sys.path

    for warehouse_type in warehouse_types:
        type_qtm = qtm if warehouse_type == "adaptive" else None

        for scenario in scenarios:
            logger.info("\n" + "=" * 80)
            qtm_label = f" QTM={type_qtm}" if type_qtm is not None else ""
            logger.info(
                f"❄️  {warehouse_type.upper()} / {scenario.upper()}{qtm_label} "
                f"/ sizes: {warehouse_sizes}"
            )
            logger.info("=" * 80)

            sf_benchmark = SnowflakeBenchmark(
                run_id=run_id,
                warehouse_type=warehouse_type,
                qtm=type_qtm,
            )
            sf_benchmark.connect()
            try:
                _run_one_scenario(
                    sf_benchmark,
                    scenario=scenario,
                    warehouse_sizes=warehouse_sizes,
                    query_nums=query_nums,
                    num_runs=num_runs,
                )
            finally:
                sf_benchmark.disconnect()

    logger.info("\n" + "=" * 80)
    logger.info(f"✅ Experiment complete. Run ID: {run_id}")
    logger.info("=" * 80)
    logger.info("\nNext steps:")
    logger.info("  1. Wait ~90 minutes for ACCOUNT_USAGE to settle.")
    logger.info("  2. Enrich:    uv run snowflake/enrich_results.py")
    logger.info("  3. Transform: uv run common/transformations/run_transformations.py")
    logger.info("  4. Refresh viz data: python visualization/update_data.py")


def _parse_csv(arg: str, valid: List[str], label: str) -> List[str]:
    items = [x.strip() for x in arg.split(",") if x.strip()]
    for x in items:
        if x not in valid:
            logger.error(f"Invalid {label}: {x!r}. Must be one of: {valid}")
            sys.exit(1)
    return items


def main():
    parser = argparse.ArgumentParser(
        description="Snowflake Adaptive vs Gen1 TPC-H Benchmark Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full sweep: both gen1 and adaptive, all 4 sizes, sequential scenario
  python main.py --warehouse-type both --scenarios sequential

  # Adaptive concurrent at QTM=2 (fresh warehouses)
  python main.py --warehouse-type adaptive --scenarios concurrent --qtm 2

  # Adaptive concurrent at QTM=8 (run separately so QTM=8 gets its own warehouse)
  python main.py --warehouse-type adaptive --scenarios concurrent --qtm 8

  # Gen1 concurrent (multi-cluster MAX=4, QTM ignored)
  python main.py --warehouse-type gen1 --scenarios concurrent

  # DML (delete+insert) on both types at default QTM
  python main.py --warehouse-type both --scenarios dml

  # Limit to one size
  python main.py --warehouse-type adaptive --scenarios sequential --sizes medium
        """,
    )
    parser.add_argument(
        "--warehouse-type",
        choices=["gen1", "adaptive", "both"],
        default="both",
        help="Which warehouse generation(s) to run. 'both' runs gen1 then adaptive "
             "with the same run_id. (default: both)",
    )
    parser.add_argument(
        "--qtm",
        type=int,
        default=DEFAULT_QTM,
        help=f"QUERY_THROUGHPUT_MULTIPLIER for adaptive runs (default: {DEFAULT_QTM}). "
             "Ignored for gen1. Run twice with different --qtm values to compare "
             "throughput settings (each gets a fresh warehouse).",
    )
    parser.add_argument(
        "--sizes",
        type=str,
        default=",".join(WAREHOUSE_SIZES),
        help=f"Comma-separated warehouse sizes. Choices: {WAREHOUSE_SIZES}. "
             f"(default: all four)",
    )
    parser.add_argument(
        "--scenarios",
        type=str,
        default="sequential",
        help=f"Comma-separated scenarios. Choices: {VALID_SCENARIOS}. "
             "(default: sequential)",
    )
    parser.add_argument(
        "--queries",
        type=str,
        help="Comma-separated query numbers (e.g., '1,2,3') or a range ('1-5'). "
             "Default: all 22 TPC-H queries.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of times to execute each query for the sequential scenario "
             "(a longer continuous workload on the same warehouse). Ignored for "
             "concurrent/dml scenarios. (default: 1)",
    )
    args = parser.parse_args()

    # Parse queries
    query_nums: Optional[List[int]] = None
    if args.queries:
        try:
            if "-" in args.queries:
                start, end = args.queries.split("-")
                query_nums = list(range(int(start), int(end) + 1))
            else:
                query_nums = [int(q.strip()) for q in args.queries.split(",")]
        except Exception:
            logger.error(f"Invalid query format: {args.queries}")
            sys.exit(1)

    sizes = _parse_csv(args.sizes, WAREHOUSE_SIZES, "size")
    scenarios = _parse_csv(args.scenarios, VALID_SCENARIOS, "scenario")
    warehouse_types = (
        WAREHOUSE_TYPES if args.warehouse_type == "both" else [args.warehouse_type]
    )

    try:
        run_experiment(
            warehouse_types=warehouse_types,
            warehouse_sizes=sizes,
            scenarios=scenarios,
            qtm=args.qtm,
            query_nums=query_nums,
            num_runs=args.runs,
        )
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Benchmark failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
