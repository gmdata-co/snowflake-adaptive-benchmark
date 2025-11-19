"""
Validate TPC-H table row counts across Snowflake and Databricks.

This script compares row counts for all TPC-H tables between Snowflake and
Databricks, displaying differences and validating against expected counts.
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from common.logging_config import get_logger
from common.connections import SnowflakeConnection, DatabricksConnection

# Import configs
from snowflake.config import (
    SNOWFLAKE_CONNECTION,
    SNOWFLAKE_ROLE,
)
from databricks.config import (
    DATABRICKS_HOST,
    DATABRICKS_TOKEN,
    CATALOG as DATABRICKS_CATALOG,
    SCHEMA as DATABRICKS_SCHEMA,
)

logger = get_logger(__name__)

# TPC-H SF1000 tables
TABLES = [
    "region",
    "nation",
    "supplier",
    "customer",
    "part",
    "partsupp",
    "orders",
    "lineitem",
]

# Expected row counts for TPC-H SF1000
EXPECTED_ROW_COUNTS = {
    "region": 5,
    "nation": 25,
    "supplier": 10_000_000,  # 10M
    "customer": 150_000_000,  # 150M
    "part": 200_000_000,  # 200M
    "partsupp": 800_000_000,  # 800M
    "orders": 1_500_000_000,  # 1.5B
    "lineitem": 6_000_000_000,  # 6B
}


def get_row_count_snowflake(connection, table_name: str) -> int | None:
    """
    Get row count for a Snowflake table.

    Args:
        connection: Snowflake connection object
        table_name: Name of the table

    Returns:
        Row count or None if error/table not found
    """
    try:
        cursor = connection.get_cursor()
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting row count for {table_name}: {e}")
        return None


def get_row_count_databricks(connection, table_name: str) -> int | None:
    """
    Get row count for a Databricks table.

    Uses fetchall_arrow to avoid pandas conversion issues with large integers.

    Args:
        connection: Databricks connection object
        table_name: Name of the table

    Returns:
        Row count or None if error/table not found
    """
    try:
        # Use the underlying connection object to get a cursor
        cursor = connection.connection.cursor()
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
        # Use fetchall_arrow to avoid pandas conversion issues
        arrow_table = cursor.fetchall_arrow()
        cursor.close()

        # Convert arrow table to pandas and extract the count
        df = arrow_table.to_pandas()
        return int(df.iloc[0, 0])
    except Exception as e:
        logger.error(f"Error getting row count for {table_name}: {e}")
        return None


def get_snowflake_counts() -> dict[str, int | None]:
    """
    Get row counts from Snowflake for all tables.

    Returns:
        Dictionary mapping table name to row count (or None if error)
    """
    counts = {}
    connection = None

    try:
        logger.info("=" * 70)
        logger.info("Connecting to Snowflake...")

        # Use Snowflake's sample TPC-H data instead of custom database
        # The sample data is available at SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000
        connection = SnowflakeConnection(
            connection_name=SNOWFLAKE_CONNECTION,
            role=SNOWFLAKE_ROLE,
            database="SNOWFLAKE_SAMPLE_DATA",
            schema="TPCH_SF1000",
        )
        connection.connect()
        logger.info("✅ Connected to Snowflake: SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000")

        for table in TABLES:
            count = get_row_count_snowflake(connection, table)
            counts[table] = count
            if count is not None:
                logger.info(f"  {table:12s}: {count:>15,} rows")
            else:
                logger.warning(f"  {table:12s}: ⚠️  Unable to get count")

    except Exception as e:
        logger.error(f"❌ Failed to connect to Snowflake: {e}")
        # Return None for all tables if connection fails
        counts = {table: None for table in TABLES}

    finally:
        if connection and connection.is_connected():
            connection.disconnect()
            logger.info("Disconnected from Snowflake")

    return counts


def get_databricks_counts() -> dict[str, int | None]:
    """
    Get row counts from Databricks for all tables.

    Returns:
        Dictionary mapping table name to row count (or None if error)
    """
    counts = {}
    connection = None
    warehouse_manager = None
    warehouse_id = None

    try:
        logger.info("=" * 70)
        logger.info("Connecting to Databricks...")

        # Create a temporary warehouse for validation
        from databricks.warehouse_manager import WarehouseManager

        warehouse_manager = WarehouseManager(run_id="validation")
        warehouse_id = warehouse_manager.create_warehouse("xsmall", "validation")
        logger.info(f"Created temporary warehouse for validation: {warehouse_id}")

        connection = DatabricksConnection(
            host=DATABRICKS_HOST,
            token=DATABRICKS_TOKEN,
            warehouse_id=warehouse_id,
            catalog=DATABRICKS_CATALOG,
            schema=DATABRICKS_SCHEMA,
        )
        connection.connect()
        logger.info(
            f"✅ Connected to Databricks: {DATABRICKS_CATALOG}.{DATABRICKS_SCHEMA}"
        )

        for table in TABLES:
            count = get_row_count_databricks(connection, table)
            counts[table] = count
            if count is not None:
                logger.info(f"  {table:12s}: {count:>15,} rows")
            else:
                logger.warning(f"  {table:12s}: ⚠️  Unable to get count")

    except Exception as e:
        logger.error(f"❌ Failed to connect to Databricks: {e}")
        # Return None for all tables if connection fails
        counts = {table: None for table in TABLES}

    finally:
        if connection and connection.is_connected():
            connection.disconnect()
            logger.info("Disconnected from Databricks")

        # Clean up temporary warehouse
        if warehouse_manager and warehouse_id:
            warehouse_name = warehouse_manager.get_warehouse_name("xsmall", "validation")
            warehouse_manager.destroy_warehouse(warehouse_id, warehouse_name)
            logger.info("Cleaned up temporary validation warehouse")

    return counts


def calculate_difference(sf_count: int | None, dbx_count: int | None) -> tuple[int | None, float | None]:
    """
    Calculate the difference and percentage difference between two counts.

    Args:
        sf_count: Snowflake row count
        dbx_count: Databricks row count

    Returns:
        Tuple of (difference, percentage_difference)
    """
    if sf_count is None or dbx_count is None:
        return None, None

    diff = dbx_count - sf_count
    if sf_count == 0:
        pct_diff = None
    else:
        pct_diff = (diff / sf_count) * 100

    return diff, pct_diff


def validate_row_counts():
    """
    Main validation function that compares row counts across platforms.
    """
    logger.info("=" * 70)
    logger.info("TPC-H TABLE ROW COUNT VALIDATION")
    logger.info("=" * 70)

    # Get counts from both platforms
    sf_counts = get_snowflake_counts()
    dbx_counts = get_databricks_counts()

    # Build comparison data
    data = []
    for table in TABLES:
        sf_count = sf_counts.get(table)
        dbx_count = dbx_counts.get(table)
        expected_count = EXPECTED_ROW_COUNTS.get(table)
        diff, pct_diff = calculate_difference(sf_count, dbx_count)

        data.append(
            {
                "table_name": table,
                "expected_rows": expected_count,
                "snowflake_rows": sf_count,
                "dbx_rows": dbx_count,
                "difference": diff,
                "diff_pct": pct_diff,
            }
        )

    # Create DataFrame
    df = pd.DataFrame(data)

    # Display results
    logger.info("=" * 70)
    logger.info("ROW COUNT COMPARISON")
    logger.info("=" * 70)

    # Format the DataFrame for display
    pd.options.display.float_format = "{:,.2f}".format
    df_display = df.copy()

    # Format numeric columns with thousands separators
    for col in ["expected_rows", "snowflake_rows", "dbx_rows", "difference"]:
        df_display[col] = df_display[col].apply(
            lambda x: f"{x:,}" if pd.notna(x) else "N/A"
        )

    # Format percentage
    df_display["diff_pct"] = df_display["diff_pct"].apply(
        lambda x: f"{x:+.4f}%" if pd.notna(x) else "N/A"
    )

    # Log the DataFrame as a formatted table
    logger.info("\n" + df_display.to_string(index=False))

    # Summary statistics
    logger.info("=" * 70)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 70)

    # Check for mismatches
    mismatches = df[
        (df["snowflake_rows"].notna())
        & (df["dbx_rows"].notna())
        & (df["snowflake_rows"] != df["dbx_rows"])
    ]

    if len(mismatches) > 0:
        logger.warning(f"⚠️  Found {len(mismatches)} table(s) with row count differences:")
        for _, row in mismatches.iterrows():
            logger.warning(
                f"  {row['table_name']:12s}: "
                f"Snowflake={row['snowflake_rows']:>15,}, "
                f"Databricks={row['dbx_rows']:>15,}, "
                f"Diff={row['difference']:>15,} ({row['diff_pct']:+.4f}%)"
            )
    else:
        matching_tables = df[
            (df["snowflake_rows"].notna())
            & (df["dbx_rows"].notna())
            & (df["snowflake_rows"] == df["dbx_rows"])
        ]
        logger.info(f"✅ All {len(matching_tables)} table(s) have matching row counts!")

    # Check for missing data
    missing_sf = df[df["snowflake_rows"].isna()]
    missing_dbx = df[df["dbx_rows"].isna()]

    if len(missing_sf) > 0:
        logger.warning(
            f"⚠️  Missing Snowflake data for {len(missing_sf)} table(s): "
            + ", ".join(missing_sf["table_name"].tolist())
        )

    if len(missing_dbx) > 0:
        logger.warning(
            f"⚠️  Missing Databricks data for {len(missing_dbx)} table(s): "
            + ", ".join(missing_dbx["table_name"].tolist())
        )

    # Validate against expected counts
    logger.info("=" * 70)
    logger.info("EXPECTED COUNT VALIDATION (TPC-H SF1000)")
    logger.info("=" * 70)

    for _, row in df.iterrows():
        table = row["table_name"]
        expected = row["expected_rows"]

        # Check Snowflake
        if pd.notna(row["snowflake_rows"]):
            if row["snowflake_rows"] == expected:
                logger.info(f"✅ {table:12s} (Snowflake): matches expected count")
            else:
                logger.warning(
                    f"⚠️  {table:12s} (Snowflake): "
                    f"expected {expected:,}, got {row['snowflake_rows']:,}"
                )

        # Check Databricks
        if pd.notna(row["dbx_rows"]):
            if row["dbx_rows"] == expected:
                logger.info(f"✅ {table:12s} (Databricks): matches expected count")
            else:
                logger.warning(
                    f"⚠️  {table:12s} (Databricks): "
                    f"expected {expected:,}, got {row['dbx_rows']:,}"
                )

    logger.info("=" * 70)
    logger.info("Validation complete!")
    logger.info("=" * 70)


if __name__ == "__main__":
    validate_row_counts()
