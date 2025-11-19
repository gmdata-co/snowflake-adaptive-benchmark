"""
Dump TPCH tables from Snowflake to S3 stage.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import from common
parent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(parent_dir))

from dotenv import load_dotenv  # noqa: E402
from common.connections.snowflake_connection import SnowflakeConnection  # noqa: E402
from common.logging_config import get_logger  # noqa: E402

logger = get_logger(__name__)

# Load environment variables
load_dotenv()

# Tables to dump
TABLES_TO_DUMP = [
    'SUPPLIER',
    'PART',
    'PARTSUPP',
    'ORDERS'
]

SOURCE_DATABASE = 'SNOWFLAKE_SAMPLE_DATA'
SOURCE_SCHEMA = 'TPCH_SF1000'
TARGET_DATABASE = 'BENCHMARK'
TARGET_SCHEMA = 'BENCHMARK'
STAGE_NAME = 'S3_TPCH_EXPORT'


def dump_table_to_s3(conn: SnowflakeConnection, table_name: str):
    """
    Dump a table to S3 stage using COPY INTO command.

    Args:
        conn: SnowflakeConnection instance
        table_name: Name of the table to dump
    """
    # Construct the COPY INTO command
    # Using Parquet format for efficient storage and compatibility with Databricks
    copy_command = f"""
    COPY INTO @{TARGET_DATABASE}.{TARGET_SCHEMA}.{STAGE_NAME}/{table_name.lower()}/
    FROM {SOURCE_DATABASE}.{SOURCE_SCHEMA}.{table_name}
    FILE_FORMAT = (
        TYPE = PARQUET
        COMPRESSION = SNAPPY
    )
    OVERWRITE = TRUE
    MAX_FILE_SIZE = 268435456
    HEADER = TRUE
    """

    logger.info(f"Starting dump of {table_name}...")
    logger.info(f"Executing: {copy_command.strip()}")

    cursor = conn.execute_query(copy_command)

    # Get results
    results = cursor.fetchall()

    # Log results
    for row in results:
        logger.info(f"  Result: {row}")

    cursor.close()
    logger.info(f"Successfully dumped {table_name} to @{STAGE_NAME}/{table_name.lower()}/")



def main():
    """Main function to dump all tables."""
    logger.info("Starting table dump process...")
    logger.info(f"Source: {SOURCE_DATABASE}.{SOURCE_SCHEMA}")
    logger.info(f"Target: @{STAGE_NAME}")
    logger.info(f"Tables to dump: {', '.join(TABLES_TO_DUMP)}")

    # Get connection name from environment
    connection_name = os.getenv('SNOWFLAKE_CONNECTION')
    if not connection_name:
        raise ValueError("SNOWFLAKE_CONNECTION environment variable not set")

    # Create Snowflake connection
    conn = SnowflakeConnection(
        connection_name=connection_name,
        role='BENCHMARK',
        database=TARGET_DATABASE,
        schema=TARGET_SCHEMA
    )

    try:
        # Connect to Snowflake
        conn.connect()

        # Dump each table
        for table_name in TABLES_TO_DUMP:
            dump_table_to_s3(conn, table_name)

        logger.info("All tables dumped successfully!")

    except Exception as e:
        logger.error(f"Error in main process: {e}")
        raise
    finally:
        conn.disconnect()


if __name__ == "__main__":
    main()
