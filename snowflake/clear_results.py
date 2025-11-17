#!/usr/bin/env python3
"""
Safely clear benchmark results CSV data.

Provides options to:
- Create a backup before clearing
- Clear all data
- Clear data by run_id
- Clear data by date range
"""

import argparse
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Initialize centralized logging
sys.path.insert(0, str(Path(__file__).parent.parent))
from common.logging_config import get_logger

logger = get_logger(__name__)

from config import RESULTS_DIR

RESULTS_FILE = RESULTS_DIR / "benchmark_results.csv"
BACKUP_DIR = RESULTS_DIR / "backups"


def create_backup(results_file: Path) -> Path:
    """
    Create a timestamped backup of the results file.

    Args:
        results_file: Path to the results CSV file

    Returns:
        Path to the backup file
    """
    if not results_file.exists():
        logger.warning(f"Results file not found: {results_file}")
        return None

    # Create backup directory if it doesn't exist
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Create timestamped backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"benchmark_results_{timestamp}.csv"

    # Copy file
    shutil.copy2(results_file, backup_file)
    logger.info(f"✅ Created backup: {backup_file}")

    return backup_file


def clear_all(results_file: Path, backup: bool = True):
    """
    Clear all data from the results file (keeps header).

    Args:
        results_file: Path to the results CSV file
        backup: Whether to create a backup first
    """
    if not results_file.exists():
        logger.warning(f"Results file not found: {results_file}")
        return

    # Load data to check size
    df = pd.read_csv(results_file)
    row_count = len(df)

    if row_count == 0:
        logger.info("Results file is already empty.")
        return

    # Show what will be deleted
    logger.info(f"\nAbout to clear {row_count} rows from {results_file}")

    # Create backup if requested
    if backup:
        backup_file = create_backup(results_file)
        if not backup_file:
            logger.error("Failed to create backup. Aborting.")
            return

    # Confirm
    response = input("\nAre you sure you want to clear all data? (yes/no): ")
    if response.lower() != "yes":
        logger.info("Cancelled.")
        return

    # Write header only
    df.iloc[0:0].to_csv(results_file, index=False)
    logger.info(f"✅ Cleared all data from {results_file}")
    logger.info(f"  Removed {row_count} rows")


def clear_by_run_id(results_file: Path, run_id: str, backup: bool = True):
    """
    Clear data for a specific run_id.

    Args:
        results_file: Path to the results CSV file
        run_id: Run ID to clear
        backup: Whether to create a backup first
    """
    if not results_file.exists():
        logger.warning(f"Results file not found: {results_file}")
        return

    # Load data
    df = pd.read_csv(results_file)

    # Filter by run_id
    to_remove = df[df["run_id"] == run_id]
    row_count = len(to_remove)

    if row_count == 0:
        logger.info(f"No rows found with run_id: {run_id}")
        return

    # Show what will be deleted
    logger.info(f"\nAbout to remove {row_count} rows with run_id: {run_id}")
    logger.info(
        f"  Timestamp: {to_remove['timestamp'].min()} to {to_remove['timestamp'].max()}"
    )
    logger.info(f"  Warehouses: {to_remove['warehouse_size'].unique().tolist()}")
    logger.info(f"  Queries: {sorted(to_remove['query_num'].unique().tolist())}")

    # Create backup if requested
    if backup:
        backup_file = create_backup(results_file)
        if not backup_file:
            logger.error("Failed to create backup. Aborting.")
            return

    # Confirm
    response = input("\nAre you sure you want to remove this data? (yes/no): ")
    if response.lower() != "yes":
        logger.info("Cancelled.")
        return

    # Remove rows
    df_filtered = df[df["run_id"] != run_id]
    df_filtered.to_csv(results_file, index=False)
    logger.info(f"✅ Removed {row_count} rows from {results_file}")


def list_runs(results_file: Path):
    """
    List all run_ids in the results file with summary info.

    Args:
        results_file: Path to the results CSV file
    """
    if not results_file.exists():
        logger.warning(f"Results file not found: {results_file}")
        return

    # Load data
    df = pd.read_csv(results_file)

    if len(df) == 0:
        logger.info("Results file is empty.")
        return

    logger.info("\n" + "=" * 100)
    logger.info("RUN SUMMARY")
    logger.info("=" * 100)

    # Group by run_id
    for run_id, group in df.groupby("run_id"):
        logger.info(f"\nRun ID: {run_id}")
        logger.info(
            f"  Timestamp: {group['timestamp'].min()} to {group['timestamp'].max()}"
        )
        logger.info(f"  Platform: {group['platform'].iloc[0]}")
        logger.info(
            f"  Warehouses: {', '.join(sorted(group['warehouse_size'].unique()))}"
        )
        logger.info(f"  Queries: {len(group['query_num'].unique())} queries")
        logger.info(f"  Total executions: {len(group)}")

        # Check if enriched
        enriched = group["compilation_time_ms"].notna().sum()
        if enriched > 0:
            logger.info(f"  Enriched: {enriched}/{len(group)} rows")

    logger.info("\n" + "=" * 100)
    logger.info(f"Total rows: {len(df)}")
    logger.info(f"Total runs: {df['run_id'].nunique()}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Safely clear benchmark results CSV data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all runs
  uv run snowflake/clear_results.py --list

  # Clear all data (with backup)
  uv run snowflake/clear_results.py --clear-all

  # Clear specific run_id
  uv run snowflake/clear_results.py --clear-run <run_id>

  # Clear without creating backup (not recommended)
  uv run snowflake/clear_results.py --clear-all --no-backup
        """,
    )

    parser.add_argument(
        "--file",
        type=Path,
        default=RESULTS_FILE,
        help=f"Path to results CSV file (default: {RESULTS_FILE})",
    )

    parser.add_argument(
        "--list", action="store_true", help="List all runs in the results file"
    )

    parser.add_argument(
        "--clear-all", action="store_true", help="Clear all data from the results file"
    )

    parser.add_argument(
        "--clear-run",
        type=str,
        metavar="RUN_ID",
        help="Clear data for a specific run_id",
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create a backup before clearing (not recommended)",
    )

    args = parser.parse_args()

    # Check if file exists
    if not args.file.exists() and not args.list:
        logger.error(f"Results file not found: {args.file}")
        return 1

    # Execute commands
    if args.list:
        list_runs(args.file)
    elif args.clear_all:
        clear_all(args.file, backup=not args.no_backup)
    elif args.clear_run:
        clear_by_run_id(args.file, args.clear_run, backup=not args.no_backup)
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
