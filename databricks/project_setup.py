#!/usr/bin/env python3
"""
Databricks vs Snowflake Benchmarking Project Setup

This script sets up the catalog, schema, and SQL warehouses for TPC-H SF1000
benchmarking according to the project plan requirements.

Requirements:
- Create BENCHMARK catalog and schema
- Create SQL warehouses (X-Small, Small, Large) with appropriate auto-stop
- Set up proper permissions
- Verify connectivity

Based on Snowflake's project_setup.sql approach
"""

import os
import sys
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import (
    CreateWarehouseRequestWarehouseType,
    SpotInstancePolicy,
    EndpointConfPair,
)

# Initialize centralized logging
sys.path.insert(0, str(Path(__file__).parent.parent))
from common.logging_config import get_logger

logger = get_logger(__name__)

# Configuration matching project plan
# Use existing catalog (creating new catalog requires storage configuration)
CATALOG_NAME = os.environ.get("DATABRICKS_CATALOG", "benchmark_catalog")
SCHEMA_NAME = "benchmark"  # Schema for TPC-H tables (scale factor agnostic)

# Warehouse configurations based on project plan Section 2
# Mapping to Snowflake equivalents (Databricks is "minus 1 size"):
# - Small = Snowflake Medium (Tier 1 - smallest)
# - Medium = Snowflake Large (Tier 2 - medium)
# - Large = Snowflake X-Large (Tier 3 - largest)

WAREHOUSES = {
    "small": {
        "name": "benchmark_wh_small",
        "cluster_size": "Small",  # Primary baseline
        "comment": "Small warehouse for tier 1 testing (equivalent to Snowflake Medium)",
        "snowflake_equivalent": "MEDIUM",
    },
    "medium": {
        "name": "benchmark_wh_medium",
        "cluster_size": "Medium",  # Mid-tier
        "comment": "Medium warehouse for tier 2 testing (equivalent to Snowflake Large)",
        "snowflake_equivalent": "LARGE",
    },
    "large": {
        "name": "benchmark_wh_large",
        "cluster_size": "Large",
        "comment": "Large warehouse for tier 3 testing (equivalent to Snowflake X-Large)",
        "snowflake_equivalent": "X-LARGE",
    },
}

# Auto-stop configuration (equivalent to Snowflake's 2-minute auto-suspend)
AUTO_STOP_MINS = 10  # Databricks minimum is 10 minutes


def setup_catalog_and_schema(w: WorkspaceClient):
    """Create schema for benchmarking (using existing catalog)."""
    logger.info("\n" + "=" * 70)
    logger.info("STEP 1: VERIFY CATALOG AND CREATE SCHEMA")
    logger.info("=" * 70)

    try:
        # Verify catalog exists (don't create if using 'main')
        logger.info(f"\nVerifying catalog: {CATALOG_NAME}")
        try:
            catalog = w.catalogs.get(CATALOG_NAME)
            logger.info(f"✅ Catalog exists: {CATALOG_NAME}")
            logger.info(f"  Owner: {catalog.owner}")
        except Exception as e:
            logger.error(f"❌ Catalog {CATALOG_NAME} not found: {e}")
            logger.info("  Please create the catalog first or use an existing one")
            return False

        # Create schema
        logger.info(f"\nCreating schema: {CATALOG_NAME}.{SCHEMA_NAME}")
        try:
            w.schemas.create(
                name=SCHEMA_NAME,
                catalog_name=CATALOG_NAME,
                comment="Schema for TPC-H benchmark tables (scale factor agnostic)",
            )
            logger.info(f"✅ Created schema: {CATALOG_NAME}.{SCHEMA_NAME}")
        except Exception as e:
            if "SCHEMA_ALREADY_EXISTS" in str(e) or "already exists" in str(e):
                logger.info(f"  Schema {SCHEMA_NAME} already exists, skipping")
            else:
                raise

        return True

    except Exception as e:
        logger.error(f"❌ Failed to setup schema: {e}")
        return False


def create_warehouse(w: WorkspaceClient, warehouse_key: str, config: dict):
    """Create a single SQL warehouse."""
    warehouse_name = config["name"]

    logger.info(f"\nCreating warehouse: {warehouse_name}")
    logger.info(f"  Size: {config['cluster_size']}")
    logger.info(f"  Snowflake equivalent: {config['snowflake_equivalent']}")

    try:
        warehouse = w.warehouses.create(
            name=warehouse_name,
            cluster_size=config["cluster_size"],
            warehouse_type=CreateWarehouseRequestWarehouseType.PRO,
            auto_stop_mins=AUTO_STOP_MINS,
            enable_serverless_compute=True,  # This creates a Serverless SQL Warehouse (most similar to Snowflake)
            max_num_clusters=1,  # Required when enable_serverless_compute=True
            spot_instance_policy=SpotInstancePolicy.COST_OPTIMIZED,
            tags=EndpointConfPair(key="purpose", value="tpch_benchmark"),
        )

        logger.info(f"✅ Created warehouse: {warehouse_name}")
        logger.info(f"  ID: {warehouse.id}")
        if warehouse.warehouse_type:
            logger.info(f"  Type: {warehouse.warehouse_type.value}")
        logger.info(f"  Auto-stop: {AUTO_STOP_MINS} minutes")

        return warehouse.id

    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info(f"  Warehouse {warehouse_name} already exists, skipping")
            # Get existing warehouse ID
            warehouses = list(w.warehouses.list())
            for wh in warehouses:
                if wh.name == warehouse_name:
                    return wh.id
            return None
        else:
            logger.error(f"❌ Failed to create warehouse {warehouse_name}: {e}")
            return None


def setup_warehouses(w: WorkspaceClient):
    """Create all SQL warehouses for benchmarking."""
    logger.info("\n" + "=" * 70)
    logger.info("STEP 2: CREATE SQL WAREHOUSES")
    logger.info("=" * 70)
    logger.info("\nBased on project plan Section 2: Compute Size Equivalents")

    warehouse_ids = {}

    for key, config in WAREHOUSES.items():
        warehouse_id = create_warehouse(w, key, config)
        if warehouse_id:
            warehouse_ids[key] = warehouse_id

    return warehouse_ids


def verify_setup(w: WorkspaceClient, warehouse_ids: dict):
    """Verify the setup is complete."""
    logger.info("\n" + "=" * 70)
    logger.info("STEP 3: VERIFY SETUP")
    logger.info("=" * 70)

    # Check catalog
    logger.info(f"\n✅ Verifying catalog: {CATALOG_NAME}")
    try:
        catalog = w.catalogs.get(CATALOG_NAME)
        logger.info(f"  Name: {catalog.name}")
        logger.info(f"  Owner: {catalog.owner}")
    except Exception as e:
        logger.error(f"❌ Catalog verification failed: {e}")
        return False

    # Check schema
    logger.info(f"\n✅ Verifying schema: {CATALOG_NAME}.{SCHEMA_NAME}")
    try:
        schema = w.schemas.get(f"{CATALOG_NAME}.{SCHEMA_NAME}")
        logger.info(f"  Full name: {schema.full_name}")
        logger.info(f"  Owner: {schema.owner}")
    except Exception as e:
        logger.error(f"❌ Schema verification failed: {e}")
        return False

    # Check warehouses
    logger.info("\n✅ Verifying SQL warehouses:")
    all_warehouses = list(w.warehouses.list())
    for key, config in WAREHOUSES.items():
        found = False
        for wh in all_warehouses:
            if wh.name == config["name"]:
                found = True
                status = "🟢 RUNNING" if wh.state.value == "RUNNING" else "⚪ STOPPED"
                logger.info(f"  {status} {wh.name}")
                logger.info(f"      ID: {wh.id}")
                logger.info(f"      Size: {wh.cluster_size}")
                break
        if not found:
            logger.warning(f"  ⚠ Warehouse {config['name']} not found")

    return True


def print_summary(warehouse_ids: dict):
    """Print setup summary and next steps."""
    logger.info("\n" + "=" * 70)
    logger.info("SETUP COMPLETE")
    logger.info("=" * 70)

    logger.info("\n📦 Created Resources:")
    logger.info(f"  Catalog: {CATALOG_NAME}")
    logger.info(f"  Schema: {CATALOG_NAME}.{SCHEMA_NAME}")
    logger.info(f"  Warehouses: {len(warehouse_ids)}")

    logger.info("\n🏭 Warehouse Configuration:")
    logger.info("  Update databricks/config.py with these IDs:")
    logger.info("")
    logger.info("  WAREHOUSES = {")
    for key, wh_id in warehouse_ids.items():
        if wh_id:
            logger.info(
                f'      "{key}": "{wh_id}",  # {WAREHOUSES[key]["snowflake_equivalent"]} equivalent'
            )
    logger.info("  }")

    logger.info("\n📋 Next Steps:")
    logger.info("  1. Update databricks/config.py with warehouse IDs above")
    logger.info("  2. Update CATALOG and SCHEMA settings in databricks/config.py:")
    logger.info(f'     CATALOG = "{CATALOG_NAME}"')
    logger.info(f'     SCHEMA = "{SCHEMA_NAME}"')
    logger.info("  3. Generate TPC-H dataset in Databricks")
    logger.info("  4. Run benchmarks!")

    logger.info("\n💡 Cost Reminder:")
    logger.info(
        f"  - Warehouses auto-stop after {AUTO_STOP_MINS} minutes of inactivity"
    )
    logger.info("  - Serverless warehouses bill per query (similar to Snowflake)")
    logger.info("  - Monitor costs in Databricks billing console")


def main():
    """Main entry point."""
    logger.info("=" * 70)
    logger.info("DATABRICKS BENCHMARKING PROJECT SETUP")
    logger.info("=" * 70)
    logger.info("\nThis will create:")
    logger.info(f"  - Schema: {CATALOG_NAME}.{SCHEMA_NAME}")
    logger.info("  - 3 SQL Warehouses (X-Small, Small, Large)")
    logger.info("")

    # Connect to Databricks
    logger.info("Connecting to Databricks...")
    try:
        w = WorkspaceClient()
        current_user = w.current_user.me()
        logger.info(f"✅ Connected as: {current_user.user_name}")
    except Exception as e:
        logger.error(f"❌ Failed to connect: {e}")
        logger.info("\nMake sure you have set up authentication:")
        logger.info("  export DATABRICKS_HOST='https://your-workspace.databricks.com'")
        logger.info("  export DATABRICKS_TOKEN='dapi...'")
        return 1

    # Step 1: Create catalog and schema
    if not setup_catalog_and_schema(w):
        logger.error("\n❌ Setup failed at catalog/schema creation")
        return 1

    # Step 2: Create warehouses
    warehouse_ids = setup_warehouses(w)
    if not warehouse_ids:
        logger.error("\n❌ Setup failed at warehouse creation")
        return 1

    # Step 3: Verify setup
    if not verify_setup(w, warehouse_ids):
        logger.error("\n❌ Setup verification failed")
        return 1

    # Print summary
    print_summary(warehouse_ids)

    logger.info("\n" + "=" * 70)
    logger.info("✅ Setup complete! Ready for TPC-H SF1000 benchmarking.")
    logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())
