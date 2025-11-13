#!/usr/bin/env python3
"""
Load NYC Taxi Data to Databricks

Loads NYC TLC trip data from public CloudFront/S3 storage.
This script provides a neutral dataset for fair comparison with Snowflake.

Test loading: Single month (yellow_tripdata_2024-01.parquet)
Full loading: Configurable date range
"""

import logging
from databricks import sql
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import config
from config import CATALOG, SCHEMA, WAREHOUSES

# Configuration
WAREHOUSE_ID = WAREHOUSES["small"]  # Use small warehouse for loading

# Data source
CLOUDFRONT_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/"

# Test configuration (1 month)
TEST_YEAR = 2024
TEST_MONTH = 1


def get_sql_connection():
    """Get SQL connection to Databricks warehouse."""
    host = os.environ.get("DATABRICKS_HOST")
    token = os.environ.get("DATABRICKS_TOKEN")

    if not host or not token:
        raise ValueError("DATABRICKS_HOST and DATABRICKS_TOKEN must be set")

    http_path = f"/sql/1.0/warehouses/{WAREHOUSE_ID}"

    return sql.connect(
        server_hostname=host.replace("https://", "").replace("http://", ""),
        http_path=http_path,
        access_token=token,
    )


def setup_schema():
    """Use existing benchmark schema for NYC taxi data."""
    logger.info("=" * 70)
    logger.info("USING EXISTING BENCHMARK SCHEMA")
    logger.info("=" * 70)

    with get_sql_connection() as connection:
        cursor = connection.cursor()

        # Use existing benchmark schema
        logger.info(f"\nUsing existing schema {CATALOG}.{SCHEMA}...")
        cursor.execute(f"USE CATALOG {CATALOG}")
        cursor.execute(f"USE SCHEMA {SCHEMA}")
        logger.info(f"✓ Using schema: {CATALOG}.{SCHEMA}")


def create_trips_table():
    """Create trips table with schema matching TLC yellow taxi data."""
    logger.info("\n" + "=" * 70)
    logger.info("CREATING TRIPS TABLE")
    logger.info("=" * 70)

    with get_sql_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(f"USE CATALOG {CATALOG}")
        cursor.execute(f"USE SCHEMA {SCHEMA}")

        # Create table with TLC yellow taxi schema
        logger.info("\nCreating yellow_trips table...")
        cursor.execute(f"""
            CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.yellow_trips (
                VendorID BIGINT,
                tpep_pickup_datetime TIMESTAMP,
                tpep_dropoff_datetime TIMESTAMP,
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
            USING DELTA
            COMMENT 'NYC Yellow Taxi trip data - loaded from neutral public source'
        """)
        logger.info("✓ Table created: yellow_trips")


def load_single_month(year: int, month: int):
    """Load a single month of yellow taxi data."""
    logger.info("\n" + "=" * 70)
    logger.info(f"LOADING DATA: {year}-{month:02d}")
    logger.info("=" * 70)

    filename = f"yellow_tripdata_{year}-{month:02d}.parquet"
    file_url = f"{CLOUDFRONT_BASE_URL}{filename}"

    with get_sql_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(f"USE CATALOG {CATALOG}")
        cursor.execute(f"USE SCHEMA {SCHEMA}")

        logger.info(f"\nLoading {filename} from CloudFront...")
        logger.info("This may take 1-2 minutes for ~50MB file...")

        try:
            # Load data using COPY INTO from HTTPS URL
            # Note: Databricks can read Parquet directly from HTTPS URLs
            cursor.execute(f"""
                COPY INTO {CATALOG}.{SCHEMA}.yellow_trips
                FROM '{file_url}'
                FILEFORMAT = PARQUET
                FORMAT_OPTIONS ('mergeSchema' = 'false')
                COPY_OPTIONS ('mergeSchema' = 'false')
            """)

            # Get load results
            results = cursor.fetchall()
            if results:
                logger.info("\nLoad results:")
                for row in results:
                    # COPY INTO returns: num_affected_rows, num_updated_rows
                    logger.info(f"  Rows loaded: {row[0]:,}")

            logger.info(f"\n✓ Data loaded successfully from {filename}")

        except Exception as e:
            logger.error(f"✗ Failed to load {filename}: {e}")
            logger.info("\nTrying alternative approach with CREATE TABLE AS SELECT...")

            # Alternative: Create table directly from Parquet URL
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {CATALOG}.{SCHEMA}.yellow_trips")
                cursor.execute(f"""
                    CREATE TABLE {CATALOG}.{SCHEMA}.yellow_trips
                    USING DELTA
                    COMMENT 'NYC Yellow Taxi trip data - loaded from neutral public source'
                    AS SELECT * FROM parquet.`{file_url}`
                """)
                logger.info("✓ Data loaded using CREATE TABLE AS SELECT")
            except Exception as e2:
                logger.error(f"✗ Alternative approach also failed: {e2}")
                raise


def verify_data():
    """Verify loaded data."""
    logger.info("\n" + "=" * 70)
    logger.info("VERIFYING LOADED DATA")
    logger.info("=" * 70)

    with get_sql_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(f"USE CATALOG {CATALOG}")
        cursor.execute(f"USE SCHEMA {SCHEMA}")

        # Row count
        logger.info("\n1. Row count:")
        cursor.execute("SELECT COUNT(*) FROM yellow_trips")
        result = cursor.fetchone()
        count = result[0] if result else 0
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
        if result:
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
    logger.info("NYC TAXI DATA LOADER - DATABRICKS")
    logger.info("=" * 70)
    logger.info(f"Target: {CATALOG}.{SCHEMA}")
    logger.info(f"Warehouse: {WAREHOUSE_ID}")
    logger.info(f"Test dataset: Yellow taxi {TEST_YEAR}-{TEST_MONTH:02d}")
    logger.info("=" * 70)

    try:
        # Step 1: Setup schema
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
        logger.info("2. Compare with Snowflake row counts")
        logger.info("3. Create benchmark queries")
        logger.info("4. Load more months if test is successful")

        return 0

    except Exception as e:
        logger.error(f"\n✗ Failed: {e}")
        logger.info("\nTroubleshooting:")
        logger.info("1. Check DATABRICKS_HOST and DATABRICKS_TOKEN are set")
        logger.info("2. Run: source ~/.zshrc")
        logger.info("3. Verify warehouse is running")
        logger.info("4. Check network connectivity to CloudFront")
        return 1


if __name__ == "__main__":
    exit(main())
