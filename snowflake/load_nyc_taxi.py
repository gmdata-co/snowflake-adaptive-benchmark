#!/usr/bin/env python3
"""
Load NYC Taxi Data to Snowflake

Loads NYC TLC trip data from public CloudFront/S3 storage.
This script provides a neutral dataset for fair comparison with Databricks.

Test loading: Single month (yellow_tripdata_2024-01.parquet)
Full loading: Configurable date range
"""

import logging
import snowflake.connector
import toml
from pathlib import Path
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import config
from config import (
    SNOWFLAKE_CONNECTION,
    SNOWFLAKE_ROLE,
    SNOWFLAKE_DATABASE,
    SNOWFLAKE_SCHEMA,
    WAREHOUSES,
)

# Configuration
DATABASE = SNOWFLAKE_DATABASE
SCHEMA = SNOWFLAKE_SCHEMA
WAREHOUSE = WAREHOUSES["medium"]
ROLE = SNOWFLAKE_ROLE
CONNECTION_NAME = SNOWFLAKE_CONNECTION

# Data source
# Note: Snowflake COPY INTO doesn't support HTTPS URLs directly
# Must use S3 path instead
S3_BASE_URL = "s3://nyc-tlc/trip-data/"

# Test configuration (1 month)
TEST_YEAR = 2024
TEST_MONTH = 1


def _load_connection_config(connection_name: str) -> dict:
    """Load connection configuration from ~/.snowflake/connections.toml"""
    connections_file = Path.home() / ".snowflake" / "connections.toml"
    if not connections_file.exists():
        raise FileNotFoundError(
            f"Snowflake connections file not found: {connections_file}"
        )

    config = toml.load(connections_file)
    if connection_name not in config:
        raise ValueError(
            f"Connection '{connection_name}' not found in {connections_file}"
        )

    return config[connection_name]


def _load_private_key(private_key_path: str):
    """Load and decode the private key for JWT authentication."""
    with open(private_key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(), password=None, backend=default_backend()
        )

    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def get_connection():
    """Get Snowflake connection using JWT authentication."""
    # Load connection configuration from ~/.snowflake/connections.toml
    conn_config = _load_connection_config(CONNECTION_NAME)

    # Prepare connection parameters
    connect_params = {
        "account": conn_config["account"],
        "user": conn_config["user"],
        "role": ROLE,
        "database": DATABASE,
        "schema": SCHEMA,
        "warehouse": WAREHOUSE,
    }

    # Handle JWT authentication if configured
    if conn_config.get("authenticator") == "SNOWFLAKE_JWT":
        private_key_path = conn_config.get("private_key_path") or conn_config.get(
            "private_key_file"
        )
        if private_key_path:
            connect_params["private_key"] = _load_private_key(private_key_path)

    # Connect to Snowflake
    return snowflake.connector.connect(**connect_params)


def setup_schema():
    """Verify access to existing benchmark schema."""
    logger.info("=" * 70)
    logger.info("VERIFYING SCHEMA ACCESS")
    logger.info("=" * 70)

    with get_connection() as conn:
        cursor = conn.cursor()

        # Use existing benchmark schema
        logger.info(f"\nUsing schema {DATABASE}.{SCHEMA}...")
        cursor.execute(f"USE SCHEMA {DATABASE}.{SCHEMA}")
        logger.info(f"✓ Schema ready: {DATABASE}.{SCHEMA}")
        logger.info("  Will load data from S3 (public NYC TLC bucket)")


def create_trips_table():
    """Create trips table with schema matching TLC yellow taxi data."""
    logger.info("\n" + "=" * 70)
    logger.info("CREATING TRIPS TABLE")
    logger.info("=" * 70)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"USE SCHEMA {DATABASE}.{SCHEMA}")

        # Create table with TLC yellow taxi schema
        logger.info("\nCreating yellow_trips table...")
        cursor.execute("""
            CREATE OR REPLACE TABLE yellow_trips (
                VendorID BIGINT,
                tpep_pickup_datetime TIMESTAMP_NTZ,
                tpep_dropoff_datetime TIMESTAMP_NTZ,
                passenger_count DOUBLE,
                trip_distance DOUBLE,
                RatecodeID DOUBLE,
                store_and_fwd_flag STRING,
                PULocationID BIGINT,
                DOLocationID BIGINT,
                payment_type BIGINT,
                fare_amount DOUBLE,
                extra DOUBLE,
                mta_tax DOUBLE,
                tip_amount DOUBLE,
                tolls_amount DOUBLE,
                improvement_surcharge DOUBLE,
                total_amount DOUBLE,
                congestion_surcharge DOUBLE,
                Airport_fee DOUBLE
            )
            COMMENT = 'NYC Yellow Taxi trip data - loaded from neutral public source'
        """)
        logger.info("✓ Table created: yellow_trips")


def load_single_month(year: int, month: int):
    """Load a single month of yellow taxi data."""
    logger.info("\n" + "=" * 70)
    logger.info(f"LOADING DATA: {year}-{month:02d}")
    logger.info("=" * 70)

    filename = f"yellow_tripdata_{year}-{month:02d}.parquet"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"USE SCHEMA {DATABASE}.{SCHEMA}")

        logger.info(f"\nLoading {filename} from S3...")
        logger.info("This may take 1-2 minutes for ~50MB file...")

        try:
            # Load data using COPY INTO from S3 URL
            file_url = f"{S3_BASE_URL}{filename}"
            cursor.execute(f"""
                COPY INTO yellow_trips
                FROM '{file_url}'
                FILE_FORMAT = (TYPE = PARQUET)
                MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
                ON_ERROR = CONTINUE
            """)

            # Get load results
            results = cursor.fetchall()
            if results:
                for row in results:
                    logger.info(f"  File: {row[0]}")
                    logger.info(f"  Status: {row[1]}")
                    logger.info(f"  Rows loaded: {row[3]:,}")
                    logger.info(f"  Rows parsed: {row[2]:,}")
                    if row[4] > 0:
                        logger.warning(f"  ⚠ Errors: {row[4]}")

            logger.info(f"\n✓ Data loaded successfully from {filename}")

        except Exception as e:
            logger.error(f"✗ Failed to load {filename}: {e}")
            raise


def verify_data():
    """Verify loaded data."""
    logger.info("\n" + "=" * 70)
    logger.info("VERIFYING LOADED DATA")
    logger.info("=" * 70)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"USE SCHEMA {DATABASE}.{SCHEMA}")

        # Row count
        logger.info("\n1. Row count:")
        cursor.execute("SELECT COUNT(*) FROM yellow_trips")
        count = cursor.fetchone()[0]
        logger.info(f"   Total rows: {count:,}")

        # Date range
        logger.info("\n2. Date range:")
        cursor.execute("""
            SELECT
                MIN(tpep_pickup_datetime) as min_date,
                MAX(tpep_pickup_datetime) as max_date
            FROM yellow_trips
        """)
        result = cursor.fetchone()
        logger.info(f"   Min pickup: {result[0]}")
        logger.info(f"   Max pickup: {result[1]}")

        # Sample aggregation
        logger.info("\n3. Sample aggregation (by payment type):")
        cursor.execute("""
            SELECT
                payment_type,
                COUNT(*) as trip_count,
                ROUND(AVG(total_amount), 2) as avg_total,
                ROUND(AVG(trip_distance), 2) as avg_distance
            FROM yellow_trips
            GROUP BY payment_type
            ORDER BY payment_type
        """)
        logger.info("   Payment Type | Trips | Avg Total | Avg Distance")
        logger.info("   " + "-" * 50)
        for row in cursor.fetchall():
            logger.info(
                f"   {row[0]:12} | {row[1]:>10,} | ${row[2]:>8} | {row[3]:>6} mi"
            )

        logger.info("\n✓ Data verification complete")


def main():
    """Main entry point."""
    logger.info("=" * 70)
    logger.info("NYC TAXI DATA LOADER - SNOWFLAKE")
    logger.info("=" * 70)
    logger.info(f"Target: {DATABASE}.{SCHEMA}")
    logger.info(f"Warehouse: {WAREHOUSE}")
    logger.info(f"Test dataset: Yellow taxi {TEST_YEAR}-{TEST_MONTH:02d}")
    logger.info("=" * 70)

    try:
        # Step 1: Setup schema and stage
        setup_schema()

        # Step 2: Create trips table
        create_trips_table()

        # Step 3: Load test month
        load_single_month(TEST_YEAR, TEST_MONTH)

        # Step 4: Verify data
        verify_data()

        # Success!
        logger.info("\n" + "=" * 70)
        logger.info("✓ SUCCESS!")
        logger.info("=" * 70)
        logger.info("\nNext steps:")
        logger.info("1. Review data above")
        logger.info("2. Load same dataset to Databricks")
        logger.info("3. Compare row counts between platforms")
        logger.info("4. Create benchmark queries")

        return 0

    except Exception as e:
        logger.error(f"\n✗ Failed: {e}")
        logger.info("\nTroubleshooting:")
        logger.info("1. Check Snowflake credentials are set")
        logger.info("2. Verify warehouse is running")
        logger.info("3. Check network connectivity to CloudFront")
        return 1


if __name__ == "__main__":
    exit(main())
