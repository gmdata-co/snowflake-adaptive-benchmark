"""
Run SQL transformations to create comparison views.

This script executes SQL files in the transformations folder to create views
for comparing Snowflake and Databricks benchmark results.
"""

import logging
from pathlib import Path
import duckdb

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Run all SQL transformations in order."""
    # Paths
    db_path = Path(__file__).parent.parent.parent / "benchmark_results.duckdb"
    transformations_dir = Path(__file__).parent

    logger.info("Running SQL transformations...")
    logger.info(f"Database: {db_path}")

    # Check if database exists
    if not db_path.exists():
        logger.error(f"Database not found at {db_path}")
        logger.error("Run a benchmark first to create the database.")
        return 1

    # Connect to DuckDB
    try:
        conn = duckdb.connect(str(db_path))
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return 1

    # Check if required tables exist
    logger.info("Checking for required tables...")
    tables = conn.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
        AND table_name IN ('snowflake_results', 'databricks_results')
    """).fetchall()

    if not tables:
        logger.error("No benchmark tables found in database.")
        logger.error("Run a benchmark first to populate the database with results.")
        conn.close()
        return 1

    table_names = [t[0] for t in tables]
    logger.info(f"Found tables: {', '.join(table_names)}")

    # Get all SQL files in order
    sql_files = sorted(transformations_dir.glob("*.sql"))

    if not sql_files:
        logger.warning(f"No SQL files found in {transformations_dir}")
        conn.close()
        return 0

    # Execute each SQL file
    for sql_file in sql_files:
        logger.info(f"Running: {sql_file.name}")

        try:
            sql_content = sql_file.read_text()
            conn.execute(sql_content)
            conn.commit()  # Explicitly commit changes
            logger.info("  ✓ Complete")
        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")
            conn.close()
            return 1

    conn.close()

    logger.info("")
    logger.info("All transformations complete!")
    logger.info("")
    logger.info("View the results:")
    logger.info(f"  duckdb {db_path} -c 'SELECT * FROM platform_comparison;'")

    return 0


if __name__ == "__main__":
    exit(main())
