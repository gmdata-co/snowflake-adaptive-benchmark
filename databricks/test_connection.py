#!/usr/bin/env python3
"""
Test Databricks connectivity and setup

This script helps you verify your Databricks connection and explore your workspace.
"""

import logging
import sys
from pathlib import Path

from databricks import sql
from databricks.sdk import WorkspaceClient

# Initialize centralized logging
sys.path.insert(0, str(Path(__file__).parent.parent))
from common.logging_config import get_logger

logger = get_logger(__name__)


def test_sdk_connection():
    """Test connection using the Databricks SDK (for workspace operations)."""
    logger.info("\n" + "=" * 70)
    logger.info("TESTING DATABRICKS SDK CONNECTION")
    logger.info("=" * 70)

    try:
        # WorkspaceClient will automatically use credentials from:
        # 1. Environment variables (DATABRICKS_HOST, DATABRICKS_TOKEN)
        # 2. ~/.databrickscfg file
        # 3. Azure CLI authentication (if on Azure)
        w = WorkspaceClient()

        # Get current user info
        current_user = w.current_user.me()
        logger.info("✅ Connected to Databricks!")
        logger.info(f"  User: {current_user.user_name}")
        logger.info(f"  Display Name: {current_user.display_name}")

        # List SQL warehouses
        logger.info("\n" + "-" * 70)
        logger.info("Available SQL Warehouses:")
        logger.info("-" * 70)

        warehouses = list(w.warehouses.list())
        if not warehouses:
            logger.warning("⚠ No SQL warehouses found!")
            logger.info("  You'll need to create SQL warehouses for benchmarking.")
        else:
            for wh in warehouses:
                status = "🟢 RUNNING" if wh.state.value == "RUNNING" else "⚪ STOPPED"
                logger.info(f"{status} {wh.name}")
                logger.info(f"         ID: {wh.id}")
                logger.info(f"         Size: {wh.cluster_size}")
                logger.info(
                    f"         Type: {wh.warehouse_type.value if wh.warehouse_type else 'N/A'}"
                )
                logger.info("")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to connect: {e}")
        logger.info("\n📋 Setup Instructions:")
        logger.info("1. Create a Databricks personal access token:")
        logger.info("   - Go to your Databricks workspace")
        logger.info("   - Click your profile → Settings → Developer → Access tokens")
        logger.info("   - Click 'Generate new token'")
        logger.info("\n2. Set up authentication using ONE of these methods:")
        logger.info("\n   Option A - Environment variables (recommended for testing):")
        logger.info(
            "   export DATABRICKS_HOST='https://your-workspace.cloud.databricks.com'"
        )
        logger.info("   export DATABRICKS_TOKEN='your-token-here'")
        logger.info("\n   Option B - Config file:")
        logger.info("   Create ~/.databrickscfg with:")
        logger.info("   [DEFAULT]")
        logger.info("   host = https://your-workspace.cloud.databricks.com")
        logger.info("   token = your-token-here")
        return False


def test_sql_connection(warehouse_id: str = None):
    """Test SQL connection to a warehouse."""
    if not warehouse_id:
        logger.info("\n⚠ No warehouse ID provided, skipping SQL test")
        logger.info("  Run with a warehouse ID to test SQL connectivity:")
        logger.info("  uv run databricks/test_connection.py <warehouse-id>")
        return False

    logger.info("\n" + "=" * 70)
    logger.info("TESTING SQL CONNECTION")
    logger.info("=" * 70)
    logger.info(f"Warehouse ID: {warehouse_id}")

    try:
        import os

        # Get credentials from environment or config
        host = os.environ.get("DATABRICKS_HOST")
        token = os.environ.get("DATABRICKS_TOKEN")

        if not host:
            logger.error("❌ DATABRICKS_HOST environment variable not set")
            return False

        # Build http_path for the warehouse
        http_path = f"/sql/1.0/warehouses/{warehouse_id}"

        # Connect to SQL warehouse
        with sql.connect(
            server_hostname=host.replace("https://", "").replace("http://", ""),
            http_path=http_path,
            access_token=token,
        ) as connection:
            with connection.cursor() as cursor:
                # Test query
                cursor.execute(
                    "SELECT current_user() as user, current_catalog() as catalog, current_schema() as schema"
                )
                result = cursor.fetchone()

                logger.info("✅ SQL connection successful!")
                logger.info(f"  User: {result[0]}")
                logger.info(f"  Catalog: {result[1]}")
                logger.info(f"  Schema: {result[2]}")

                # List catalogs
                logger.info("\n" + "-" * 70)
                logger.info("Available Catalogs:")
                logger.info("-" * 70)
                cursor.execute("SHOW CATALOGS")
                for row in cursor.fetchall():
                    logger.info(f"  - {row[0]}")

                return True

    except Exception as e:
        logger.error(f"❌ SQL connection failed: {e}")
        return False


def main():
    """Main entry point."""
    import sys

    # Test SDK connection
    sdk_ok = test_sdk_connection()

    if not sdk_ok:
        logger.info("\n" + "=" * 70)
        logger.info("Please set up authentication first, then run this script again.")
        logger.info("=" * 70)
        return

    # Test SQL connection if warehouse ID provided
    if len(sys.argv) > 1:
        warehouse_id = sys.argv[1]
        test_sql_connection(warehouse_id)
    else:
        logger.info("\n" + "=" * 70)
        logger.info("NEXT STEPS")
        logger.info("=" * 70)
        logger.info("1. Choose a SQL warehouse from the list above")
        logger.info("2. Test SQL connectivity:")
        logger.info("   uv run databricks/test_connection.py <warehouse-id>")
        logger.info("\n3. Update databricks/config.py with your warehouse IDs")
        logger.info("4. Set up TPC-H dataset (we'll help with this next)")


if __name__ == "__main__":
    main()
