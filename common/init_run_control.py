"""
Initialize or reset the run_control table in duckdb.

This table controls which run_ids are used by the dbt views:
- run_type: scenario name ('normal', 'coldstart', or 'latest')
- run_id: specific run to use, or 999 for "use latest"

When run_id = 999, dbt views use their current "latest run" logic.
When run_id = <specific_value>, dbt views use that exact run.
"""

import duckdb
import sys
from pathlib import Path

# Add project root to path for imports
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from common.logging_config import get_logger  # noqa: E402

logger = get_logger(__name__)


def get_duckdb_path() -> Path:
    """Get the path to the benchmark results duckdb file."""
    # Script is in common/, duckdb is at project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    return project_root / "benchmark_results.duckdb"


def create_run_control_table(reset: bool = False) -> None:
    """
    Create the run_control table with default values.

    Args:
        reset: If True, drop existing table first. If False, skip if table exists.
    """
    db_path = get_duckdb_path()

    if not db_path.exists():
        logger.error(f"DuckDB file not found at {db_path}")
        raise FileNotFoundError(f"DuckDB file not found at {db_path}")

    logger.info(f"Connecting to DuckDB at {db_path}")

    with duckdb.connect(str(db_path)) as conn:
        # Check if table exists
        result = conn.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'main'
            AND table_name = 'run_control'
        """).fetchone()

        table_exists = result[0] > 0

        if table_exists:
            if reset:
                logger.info("Dropping existing run_control table")
                conn.execute("DROP TABLE IF EXISTS main.run_control")
            else:
                logger.info("run_control table already exists, skipping creation")
                logger.info("Use reset=True to recreate the table")
                # Show current contents
                current = conn.execute("SELECT * FROM main.run_control ORDER BY run_type").fetchall()
                logger.info("Current run_control contents:")
                for row in current:
                    logger.info(f"  {row[0]}: {row[1]}")
                return

        # Create table
        logger.info("Creating run_control table")
        conn.execute("""
            CREATE TABLE main.run_control (
                run_type TEXT PRIMARY KEY,
                run_id INTEGER NOT NULL
            )
        """)

        # Insert default values
        logger.info("Inserting default values (999 = use latest)")
        conn.execute("""
            INSERT INTO main.run_control (run_type, run_id) VALUES
                ('normal', 999),
                ('coldstart', 999),
                ('latest', 999)
        """)

        # Verify
        result = conn.execute("SELECT * FROM main.run_control ORDER BY run_type").fetchall()
        logger.info("Successfully created run_control table:")
        for row in result:
            logger.info(f"  {row[0]}: {row[1]}")


def update_run_control(run_type: str, run_id: int) -> None:
    """
    Update a specific run_type to use a different run_id.

    Args:
        run_type: The scenario ('normal', 'coldstart', or 'latest')
        run_id: The run_id to use (999 for latest, or specific run_id)
    """
    db_path = get_duckdb_path()

    logger.info(f"Updating {run_type} to use run_id {run_id}")

    with duckdb.connect(str(db_path)) as conn:
        conn.execute("""
            UPDATE main.run_control
            SET run_id = ?
            WHERE run_type = ?
        """, [run_id, run_type])

        # Verify
        result = conn.execute(
            "SELECT run_id FROM main.run_control WHERE run_type = ?",
            [run_type]
        ).fetchone()

        if result:
            logger.info(f"Successfully updated: {run_type} = {result[0]}")
        else:
            logger.warning(f"run_type '{run_type}' not found in table")


def show_run_control() -> None:
    """Display current run_control settings."""
    db_path = get_duckdb_path()

    with duckdb.connect(str(db_path)) as conn:
        result = conn.execute("SELECT * FROM main.run_control ORDER BY run_type").fetchall()

        logger.info("Current run_control settings:")
        for row in result:
            status = "latest" if row[1] == 999 else f"run_id {row[1]}"
            logger.info(f"  {row[0]}: {status}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Initialize or manage the run_control table"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate the table with default values"
    )
    parser.add_argument(
        "--update",
        nargs=2,
        metavar=("RUN_TYPE", "RUN_ID"),
        help="Update a specific run_type to a new run_id (e.g., --update normal 5)"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display current run_control settings"
    )

    args = parser.parse_args()

    if args.show:
        show_run_control()
    elif args.update:
        run_type, run_id = args.update
        update_run_control(run_type, int(run_id))
    else:
        create_run_control_table(reset=args.reset)
