#!/usr/bin/env python3
"""
Snowflake Warehouse Manager

Manages warehouse lifecycle for benchmarks: creation, destruction, suspension, resumption.
"""

from typing import List, Dict
from common.logging_config import get_logger
from .config import (
    SNOWFLAKE_ROLE,
    WAREHOUSE_SIZE_MAP,
    WAREHOUSE_PREFIX,
    WAREHOUSE_AUTO_SUSPEND,
    WAREHOUSE_AUTO_RESUME,
    WAREHOUSE_INITIALLY_SUSPENDED,
)

logger = get_logger(__name__)


class WarehouseManager:
    """Manages Snowflake warehouse lifecycle for benchmarks."""

    def __init__(self, connection, run_id: str):
        """
        Initialize warehouse manager.

        Args:
            connection: Snowflake connection object
            run_id: Run ID for warehouse naming
        """
        self.connection = connection
        self.run_id = run_id
        self.created_warehouses: List[str] = []  # Track for cleanup

    def get_warehouse_name(self, warehouse_size: str, scenario: str) -> str:
        """
        Generate warehouse name with scenario and run_id suffix.

        Args:
            warehouse_size: Warehouse size key (e.g., "small", "medium", "xlarge")
            scenario: Scenario name (e.g., "normal", "coldstart", "concurrent")

        Returns:
            Full warehouse name (e.g., "BENCHMARK_WH_MEDIUM_NORMAL_001")
        """
        size_upper = WAREHOUSE_SIZE_MAP[warehouse_size]
        scenario_upper = scenario.upper()
        return f"{WAREHOUSE_PREFIX}_{size_upper}_{scenario_upper}_{self.run_id}"

    def _execute(self, sql: str):
        """
        Execute SQL statement.

        Args:
            sql: SQL statement to execute
        """
        cursor = self.connection.cursor()
        cursor.execute(sql)
        cursor.close()

    def create_warehouse(self, warehouse_size: str, scenario: str) -> str:
        """
        Create a warehouse for this benchmark run.

        Args:
            warehouse_size: Warehouse size key (e.g., "small", "medium", "xlarge")
            scenario: Scenario name (e.g., "normal", "coldstart", "concurrent")

        Returns:
            Name of the created warehouse
        """
        warehouse_name = self.get_warehouse_name(warehouse_size, scenario)
        size_upper = WAREHOUSE_SIZE_MAP[warehouse_size]

        logger.info(f"Creating warehouse: {warehouse_name} (size: {size_upper})")

        # Need to use SYSADMIN role to create warehouse
        self._execute("USE ROLE SYSADMIN")

        create_sql = f"""CREATE WAREHOUSE IF NOT EXISTS {warehouse_name}
            WITH
            WAREHOUSE_SIZE = '{size_upper}'
            AUTO_SUSPEND = {WAREHOUSE_AUTO_SUSPEND}
            AUTO_RESUME = {str(WAREHOUSE_AUTO_RESUME).upper()}
            INITIALLY_SUSPENDED = {str(WAREHOUSE_INITIALLY_SUSPENDED).upper()}
            COMMENT = 'Ephemeral warehouse for benchmark run {self.run_id} scenario {scenario}'"""

        self._execute(create_sql)

        # Grant all privileges to BENCHMARK role so it can use and drop the warehouse
        grant_sql = f"GRANT ALL ON WAREHOUSE {warehouse_name} TO ROLE {SNOWFLAKE_ROLE}"
        self._execute(grant_sql)

        # Switch back to BENCHMARK role
        self._execute(f"USE ROLE {SNOWFLAKE_ROLE}")

        logger.info(f"✅ Created warehouse: {warehouse_name}")
        self.created_warehouses.append(warehouse_name)

        return warehouse_name

    def destroy_warehouse(self, warehouse_name: str):
        """
        Destroy a warehouse created by this benchmark.

        Args:
            warehouse_name: Name of warehouse to destroy
        """
        logger.info(f"Destroying warehouse: {warehouse_name}")

        try:
            drop_sql = f"DROP WAREHOUSE IF EXISTS {warehouse_name}"
            self._execute(drop_sql)
            logger.info(f"✅ Destroyed warehouse: {warehouse_name}")
        except Exception as e:
            logger.error(f"❌ Failed to destroy warehouse {warehouse_name}: {e}")

    def create_all_warehouses(
        self, warehouse_sizes: List[str], scenario: str
    ) -> Dict[str, str]:
        """
        Create all warehouses needed for this benchmark run.

        Args:
            warehouse_sizes: List of warehouse size keys to create
            scenario: Scenario name for warehouse naming

        Returns:
            Dictionary mapping warehouse size to warehouse name
        """
        logger.info("\n" + "=" * 70)
        logger.info(f"CREATING WAREHOUSES FOR SCENARIO: {scenario.upper()}")
        logger.info("=" * 70)

        warehouse_map = {}
        for warehouse_size in warehouse_sizes:
            warehouse_name = self.create_warehouse(warehouse_size, scenario)
            warehouse_map[warehouse_size] = warehouse_name

        logger.info("=" * 70)
        return warehouse_map

    def destroy_all_warehouses(self):
        """Destroy all warehouses created by this benchmark run."""
        if not self.created_warehouses:
            return

        logger.info("\n" + "=" * 70)
        logger.info("CLEANING UP WAREHOUSES")
        logger.info("=" * 70)

        for warehouse_name in self.created_warehouses:
            self.destroy_warehouse(warehouse_name)

        logger.info("=" * 70)

    def suspend_warehouse(self, warehouse_name: str):
        """
        Suspend a warehouse.

        Args:
            warehouse_name: Name of warehouse to suspend
        """
        logger.info(f"Suspending warehouse: {warehouse_name}")

        try:
            suspend_sql = f"ALTER WAREHOUSE {warehouse_name} SUSPEND"
            self._execute(suspend_sql)
            logger.info(f"✅ Suspended warehouse: {warehouse_name}")
        except Exception as e:
            logger.error(f"❌ Failed to suspend warehouse {warehouse_name}: {e}")
            raise

    def resume_warehouse(self, warehouse_name: str):
        """
        Resume a warehouse.

        Args:
            warehouse_name: Name of warehouse to resume
        """
        logger.info(f"Resuming warehouse: {warehouse_name}")

        try:
            resume_sql = f"ALTER WAREHOUSE {warehouse_name} RESUME"
            self._execute(resume_sql)
            logger.info(f"✅ Resumed warehouse: {warehouse_name}")
        except Exception as e:
            logger.error(f"❌ Failed to resume warehouse {warehouse_name}: {e}")
            raise

    def switch_warehouse(self, warehouse_name: str):
        """
        Switch to a different warehouse.

        Args:
            warehouse_name: Name of warehouse to switch to
        """
        self._execute(f"USE WAREHOUSE {warehouse_name}")
