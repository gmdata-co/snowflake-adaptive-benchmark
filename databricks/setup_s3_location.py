#!/usr/bin/env python3
"""Create external location for S3 bucket in Databricks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from databricks.sdk import WorkspaceClient

# Initialize centralized logging
from common.logging_config import get_logger

logger = get_logger(__name__)

S3_BUCKET = "s3://snowflake-databricks-benchmarks-benchmarks-1763063895/"
LOCATION_NAME = "snowflake_s3_stage"


def main():
    logger.info("=" * 70)
    logger.info("SETTING UP S3 EXTERNAL LOCATION")
    logger.info("=" * 70)

    try:
        # Connect to Databricks
        logger.info("\nConnecting to Databricks workspace...")
        w = WorkspaceClient()
        user = w.current_user.me()
        logger.info(f"✅ Connected as: {user.user_name}")

        # Check if location already exists
        logger.info(f"\nChecking for existing external location: {LOCATION_NAME}")
        try:
            existing = w.external_locations.get(LOCATION_NAME)
            logger.info("✅ External location already exists")
            logger.info(f"  URL: {existing.url}")
            return True
        except Exception:
            logger.info("  Not found, creating new...")

        # Create external location
        logger.info("\nCreating external location...")
        from databricks.sdk.service.catalog import ExternalLocationInfo

        location = ExternalLocationInfo(
            name=LOCATION_NAME,
            url=S3_BUCKET,
            comment="S3 stage for Snowflake unloaded data",
        )

        result = w.external_locations.create(location)
        logger.info(f"✅ Created: {result.name}")
        logger.info(f"  URL: {result.url}")

        logger.info("\n" + "=" * 70)
        logger.info("✅ EXTERNAL LOCATION READY")
        logger.info("=" * 70)
        logger.info(f"\nYou can now load data from {S3_BUCKET}")

        return True

    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
