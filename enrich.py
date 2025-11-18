#!/usr/bin/env python3
"""
Enrich Benchmark Results

Orchestrates the enrichment workflow by calling enrichment scripts in order:
1. Snowflake results enrichment (from ACCOUNT_USAGE.QUERY_HISTORY)
2. Snowflake warehouse usage loading (from ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY)
3. Databricks warehouse usage loading (from system.billing.usage)

Note: Databricks results enrichment is skipped as it's currently not working correctly.
"""

import sys
import subprocess
from pathlib import Path

from common.logging_config import get_logger

logger = get_logger(__name__)


def run_script(script_path: Path, description: str) -> int:
    """
    Run a Python script and return its exit code.

    Args:
        script_path: Path to the script to run
        description: Human-readable description of the script

    Returns:
        Exit code from the script (0 = success, non-zero = failure)
    """
    logger.info(f"\n{'=' * 80}")
    logger.info(f"Running: {description}")
    logger.info(f"Script: {script_path}")
    logger.info(f"{'=' * 80}\n")

    try:
        # Run using uv run as per project guidelines
        result = subprocess.run(
            ["uv", "run", str(script_path)],
            check=False,  # Don't raise exception on non-zero exit
            cwd=Path(__file__).parent,
        )

        if result.returncode == 0:
            logger.info(f"\n✅ {description} completed successfully\n")
        else:
            logger.error(f"\n❌ {description} failed with exit code {result.returncode}\n")

        return result.returncode

    except Exception as e:
        logger.error(f"\n❌ Failed to run {description}: {e}\n")
        return 1


def main():
    """Main entry point."""
    logger.info("\n" + "=" * 80)
    logger.info("BENCHMARK RESULTS ENRICHMENT WORKFLOW")
    logger.info("=" * 80)
    logger.info("\nThis script will enrich benchmark results with:")
    logger.info("  1. Snowflake query metrics from ACCOUNT_USAGE")
    logger.info("  2. Snowflake warehouse usage data")
    logger.info("  3. Databricks warehouse usage data")
    logger.info("\nNOTE: Run this at least 45 minutes (Snowflake) to 2 hours (Databricks)")
    logger.info("      after benchmark completion to ensure system tables are populated.")
    logger.info("=" * 80 + "\n")

    project_root = Path(__file__).parent

    # Define scripts to run in order
    scripts = [
        {
            "path": project_root / "snowflake" / "enrich_results.py",
            "description": "Snowflake Results Enrichment",
        },
        {
            "path": project_root / "snowflake" / "load_warehouse_usage.py",
            "description": "Snowflake Warehouse Usage Loading",
        },
        {
            "path": project_root / "databricks" / "load_warehouse_usage.py",
            "description": "Databricks Warehouse Usage Loading",
        },
    ]

    # Track results
    results = []

    # Run each script in order
    for script_info in scripts:
        script_path = script_info["path"]
        description = script_info["description"]

        if not script_path.exists():
            logger.error(f"❌ Script not found: {script_path}")
            return 1

        exit_code = run_script(script_path, description)
        results.append({
            "description": description,
            "exit_code": exit_code,
        })

        # Continue even if a script fails (some enrichment is better than none)
        if exit_code != 0:
            logger.warning(f"⚠ {description} failed, but continuing with remaining scripts...")

    # Print final summary
    logger.info("\n" + "=" * 80)
    logger.info("ENRICHMENT WORKFLOW SUMMARY")
    logger.info("=" * 80)

    success_count = 0
    for result in results:
        status = "✅ SUCCESS" if result["exit_code"] == 0 else "❌ FAILED"
        logger.info(f"{status}: {result['description']}")
        if result["exit_code"] == 0:
            success_count += 1

    logger.info("\n" + "-" * 80)
    logger.info(f"Results: {success_count}/{len(results)} scripts completed successfully")
    logger.info("=" * 80 + "\n")

    # Return 0 if all succeeded, 1 if any failed
    if success_count == len(results):
        logger.info("✅ All enrichment steps completed successfully!")
        return 0
    else:
        logger.warning("⚠ Some enrichment steps failed. Check logs above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
