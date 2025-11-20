#!/usr/bin/env python3
"""
Databricks Warehouse Manager

Manages warehouse lifecycle for benchmarks: creation, destruction, starting, stopping.
"""

import time
import requests
from typing import List, Dict
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import (
    CreateWarehouseRequestWarehouseType,
    SpotInstancePolicy,
)
from common.logging_config import get_logger
from .config import (
    DATABRICKS_HOST,
    DATABRICKS_TOKEN,
    WAREHOUSE_PREFIX,
    WAREHOUSE_SIZE_MAP,
    WAREHOUSE_AUTO_STOP_MINS,
    WAREHOUSE_MAX_NUM_CLUSTERS,
)

logger = get_logger(__name__)


class WarehouseManager:
    """Manages Databricks SQL warehouse lifecycle for benchmarks."""

    def __init__(self, run_id: str):
        """
        Initialize warehouse manager.

        Args:
            run_id: Run ID for warehouse naming
        """
        self.run_id = run_id
        self.workspace_client: WorkspaceClient = None
        self.created_warehouses: List[Dict[str, str]] = []  # List of {size, id, name} dicts

        # Initialize Databricks SDK client for warehouse management
        self._ensure_workspace_client()

    def _ensure_workspace_client(self):
        """Ensure WorkspaceClient is initialized."""
        if self.workspace_client is None:
            self.workspace_client = WorkspaceClient(
                host=DATABRICKS_HOST,
                token=DATABRICKS_TOKEN,
            )

    def get_warehouse_name(self, warehouse_size: str, scenario: str) -> str:
        """
        Generate warehouse name with scenario and run_id suffix.

        Args:
            warehouse_size: Warehouse size key (e.g., "xsmall", "small", "large")
            scenario: Scenario name (e.g., "normal", "coldstart", "concurrent")

        Returns:
            Full warehouse name (e.g., "benchmark_dbx_small_normal_001")
        """
        scenario_lower = scenario.lower()
        return f"{WAREHOUSE_PREFIX}_{warehouse_size}_{scenario_lower}_{self.run_id}"

    def create_warehouse(
        self, warehouse_size: str, scenario: str, max_num_clusters: int = None
    ) -> str:
        """
        Create a Serverless SQL warehouse for this benchmark run.

        Args:
            warehouse_size: Warehouse size key (e.g., "xsmall", "small", "large")
            scenario: Scenario name (e.g., "normal", "coldstart", "concurrent")
            max_num_clusters: Maximum number of clusters for multi-cluster warehouse (optional)

        Returns:
            ID of the created warehouse
        """
        warehouse_name = self.get_warehouse_name(warehouse_size, scenario)
        cluster_size = WAREHOUSE_SIZE_MAP[warehouse_size]

        # Use provided max_num_clusters or fall back to config default
        max_clusters = (
            max_num_clusters if max_num_clusters is not None else WAREHOUSE_MAX_NUM_CLUSTERS
        )

        cluster_info = f" (size: {cluster_size}, max_clusters: {max_clusters})"
        logger.info(f"Creating warehouse: {warehouse_name}{cluster_info}")

        self._ensure_workspace_client()

        # Create Serverless SQL warehouse
        warehouse = self.workspace_client.warehouses.create(
            name=warehouse_name,
            cluster_size=cluster_size,
            warehouse_type=CreateWarehouseRequestWarehouseType.PRO,
            enable_serverless_compute=True,
            max_num_clusters=max_clusters,
            auto_stop_mins=WAREHOUSE_AUTO_STOP_MINS,
            spot_instance_policy=SpotInstancePolicy.COST_OPTIMIZED,
        )

        warehouse_id = warehouse.id
        logger.info(f"✅ Created warehouse: {warehouse_name} (ID: {warehouse_id})")

        # Track for cleanup
        self.created_warehouses.append({
            "size": warehouse_size,
            "id": warehouse_id,
            "name": warehouse_name,
        })

        return warehouse_id

    def destroy_warehouse(self, warehouse_id: str, warehouse_name: str):
        """
        Destroy a warehouse created by this benchmark.

        Args:
            warehouse_id: ID of warehouse to destroy
            warehouse_name: Name of warehouse (for logging)
        """
        logger.info(f"Destroying warehouse: {warehouse_name} (ID: {warehouse_id})")

        try:
            # Add a small delay to ensure all connections have closed
            time.sleep(2)

            self._ensure_workspace_client()
            self.workspace_client.warehouses.delete(id=warehouse_id)
            logger.info(f"✅ Destroyed warehouse: {warehouse_name}")
        except Exception as e:
            logger.error(f"❌ Failed to destroy warehouse {warehouse_name}: {e}")

    def create_all_warehouses(
        self, warehouse_sizes: List[str], scenario: str, max_num_clusters: int = None
    ) -> Dict[str, str]:
        """
        Create all warehouses needed for this benchmark run.

        Args:
            warehouse_sizes: List of warehouse size keys to create
            scenario: Scenario name for warehouse naming
            max_num_clusters: Maximum number of clusters for multi-cluster warehouse (optional)

        Returns:
            Dictionary mapping warehouse size to warehouse ID
        """
        logger.info("\n" + "=" * 70)
        logger.info(f"CREATING WAREHOUSES FOR SCENARIO: {scenario.upper()}")
        logger.info("=" * 70)

        warehouse_id_map = {}
        for warehouse_size in warehouse_sizes:
            warehouse_id = self.create_warehouse(warehouse_size, scenario, max_num_clusters)
            warehouse_id_map[warehouse_size] = warehouse_id

        logger.info("=" * 70)
        return warehouse_id_map

    def destroy_all_warehouses(self):
        """Destroy all warehouses created by this benchmark run."""
        if not self.created_warehouses:
            return

        logger.info("\n" + "=" * 70)
        logger.info("CLEANING UP WAREHOUSES")
        logger.info("=" * 70)

        for warehouse_info in self.created_warehouses:
            self.destroy_warehouse(warehouse_info["id"], warehouse_info["name"])

        logger.info("=" * 70)

    def _get_warehouse_state(self, warehouse_id: str) -> str:
        """
        Get current state of a warehouse.

        Args:
            warehouse_id: ID of the warehouse

        Returns:
            State string (e.g., "RUNNING", "STOPPED", "STARTING", "STOPPING")
        """
        # Clean hostname
        hostname = DATABRICKS_HOST.replace("https://", "").replace("http://", "")
        url = f"https://{hostname}/api/2.0/sql/warehouses/{warehouse_id}"

        headers = {
            "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json().get("state", "UNKNOWN")

    def _wait_for_warehouse_state(
        self, warehouse_id: str, target_state: str, timeout: int = 300
    ):
        """
        Wait for warehouse to reach target state.

        Args:
            warehouse_id: ID of the warehouse
            target_state: Target state to wait for (e.g., "RUNNING", "STOPPED")
            timeout: Maximum time to wait in seconds
        """
        start_time = time.time()
        last_state = None
        while time.time() - start_time < timeout:
            state = self._get_warehouse_state(warehouse_id)
            if state == target_state:
                logger.info(f"✅ Warehouse {warehouse_id} is {target_state}")
                return
            # Log state changes at INFO level
            if state != last_state:
                logger.info(
                    f"Waiting for warehouse {warehouse_id} to be {target_state} (current: {state})"
                )
                last_state = state
            time.sleep(5)

        raise TimeoutError(
            f"Warehouse {warehouse_id} did not reach {target_state} within {timeout}s"
        )

    def stop_warehouse(self, warehouse_id: str, wait_for_stopped: bool = True):
        """
        Stop a warehouse using Databricks REST API.

        Args:
            warehouse_id: ID of the warehouse to stop
            wait_for_stopped: If True, wait for warehouse to fully stop (default: True)
        """
        logger.info(f"Stopping warehouse: {warehouse_id}")

        try:
            # Clean hostname
            hostname = DATABRICKS_HOST.replace("https://", "").replace("http://", "")
            url = f"https://{hostname}/api/2.0/sql/warehouses/{warehouse_id}/stop"

            headers = {
                "Authorization": f"Bearer {DATABRICKS_TOKEN}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, headers=headers)
            response.raise_for_status()

            logger.info(f"✅ Stopped warehouse: {warehouse_id}")

            # Wait for warehouse to fully stop (check status) - optional
            if wait_for_stopped:
                self._wait_for_warehouse_state(warehouse_id, "STOPPED")

        except Exception as e:
            logger.error(f"❌ Failed to stop warehouse {warehouse_id}: {e}")
            raise

    def start_warehouse(self, warehouse_id: str):
        """
        Start a warehouse using Databricks REST API.

        Args:
            warehouse_id: ID of the warehouse to start
        """
        logger.info(f"Starting warehouse: {warehouse_id}")

        try:
            # Clean hostname
            hostname = DATABRICKS_HOST.replace("https://", "").replace("http://", "")
            url = f"https://{hostname}/api/2.0/sql/warehouses/{warehouse_id}/start"

            headers = {
                "Authorization": f"Bearer {DATABRICKS_TOKEN}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, headers=headers)
            response.raise_for_status()

            logger.info(f"✅ Started warehouse: {warehouse_id}")

            # Wait for warehouse to be ready
            self._wait_for_warehouse_state(warehouse_id, "RUNNING")

        except Exception as e:
            logger.error(f"❌ Failed to start warehouse {warehouse_id}: {e}")
            raise
