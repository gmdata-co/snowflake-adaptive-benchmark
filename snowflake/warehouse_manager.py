#!/usr/bin/env python3
"""
Snowflake Warehouse Manager

Manages warehouse lifecycle for benchmarks: creation, destruction, suspension, resumption.
"""

import os
import time
from typing import List, Dict, Optional
from common.logging_config import get_logger
from .config import (
    SNOWFLAKE_ROLE,
    WAREHOUSE_SIZE_MAP,
    WAREHOUSE_PREFIX,
    WAREHOUSE_AUTO_SUSPEND,
    WAREHOUSE_AUTO_RESUME,
    WAREHOUSE_INITIALLY_SUSPENDED,
    DEFAULT_QTM,
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

    def get_warehouse_name(
        self,
        warehouse_size: str,
        scenario: str,
        warehouse_type: str = "gen1",
        qtm: Optional[int] = None,
    ) -> str:
        """
        Generate warehouse name with type/size/scenario/QTM/run_id segments.

        Each variant (different QTM, size, type) must resolve to a unique name so
        Snowflake's WAREHOUSE_METERING_HISTORY and per-query credit attribution
        produce isolated billing records per variant.

        Returns:
            e.g. "BENCHMARK_WH_ADAPTIVE_MEDIUM_CONCURRENT_QTM8_001"
                 "BENCHMARK_WH_GEN1_MEDIUM_SEQUENTIAL_001"
        """
        size_upper = WAREHOUSE_SIZE_MAP[warehouse_size]
        type_upper = warehouse_type.upper()
        scenario_upper = scenario.upper()
        parts = [WAREHOUSE_PREFIX, type_upper, size_upper, scenario_upper]
        if warehouse_type == "adaptive" and qtm is not None:
            parts.append(f"QTM{qtm}")
        parts.append(self.run_id)
        return "_".join(parts)

    def _execute(self, sql: str):
        """
        Execute SQL statement.

        Args:
            sql: SQL statement to execute
        """
        cursor = self.connection.cursor()
        cursor.execute(sql)
        cursor.close()

    def _query(self, sql: str):
        """Execute SQL and return all rows."""
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql)
            return cursor.fetchall()
        finally:
            cursor.close()

    def _warehouse_state(self, warehouse_name: str) -> Optional[str]:
        """Return the current state string (e.g. 'STARTED', 'SUSPENDED') or None."""
        rows = self._query(f"SHOW WAREHOUSES LIKE '{warehouse_name}'")
        if not rows:
            return None
        # SHOW WAREHOUSES column order is stable: name=[0], state=[1].
        return rows[0][1]

    def _wait_until_suspended(self, warehouse_name: str, timeout: int = 180):
        """
        Block until a gen1 warehouse auto-suspends, so its idle tail is billed
        into WAREHOUSE_METERING_HISTORY before we drop it.

        Real users do not drop a warehouse the instant a query finishes — it
        sits idle until AUTO_SUSPEND fires, and that idle time is real spend.
        Dropping immediately hides it; waiting captures it.

        Polls SHOW WAREHOUSES until state == 'SUSPENDED' or `timeout` seconds
        elapse (then drops anyway so cleanup never hangs forever).
        """
        deadline = time.time() + timeout
        logger.info(
            f"⏳ Waiting for {warehouse_name} to auto-suspend before drop "
            f"(captures idle billing tail)..."
        )
        while time.time() < deadline:
            state = self._warehouse_state(warehouse_name)
            if state is None:
                logger.info(f"{warehouse_name} no longer exists; nothing to wait for.")
                return
            if str(state).upper() == "SUSPENDED":
                logger.info(f"✅ {warehouse_name} is SUSPENDED; idle tail captured.")
                return
            time.sleep(10)
        logger.warning(
            f"⚠️  {warehouse_name} did not reach SUSPENDED within {timeout}s; "
            f"dropping anyway."
        )

    def create_warehouse(
        self,
        warehouse_size: str,
        scenario: str,
        warehouse_type: str = "gen1",
        qtm: Optional[int] = None,
        max_cluster_count: int = None,
        min_cluster_count: int = None,
    ) -> str:
        """
        Create a warehouse for this benchmark run.

        Args:
            warehouse_size: Warehouse size key (e.g., "small", "medium", "xlarge")
            scenario: Scenario name (e.g., "sequential", "concurrent", "dml")
            warehouse_type: "gen1" (pins GENERATION='1') or "adaptive"
                            (uses CREATE ADAPTIVE WAREHOUSE).
            qtm: QUERY_THROUGHPUT_MULTIPLIER, adaptive only. Defaults to DEFAULT_QTM.
            max_cluster_count: Multi-cluster max (gen1 only).
            min_cluster_count: Multi-cluster min (gen1 only).
        """
        if warehouse_type not in ("gen1", "adaptive"):
            raise ValueError(f"Unknown warehouse_type: {warehouse_type!r}")

        if warehouse_type == "adaptive" and qtm is None:
            qtm = DEFAULT_QTM

        warehouse_name = self.get_warehouse_name(
            warehouse_size, scenario, warehouse_type, qtm
        )
        size_upper = WAREHOUSE_SIZE_MAP[warehouse_size]

        if warehouse_type == "adaptive":
            info = f" (adaptive, perf_level: {size_upper}, qtm: {qtm})"
        elif max_cluster_count:
            info = f" (gen1, size: {size_upper}, max_clusters: {max_cluster_count})"
        else:
            info = f" (gen1, size: {size_upper})"
        logger.info(f"Creating warehouse: {warehouse_name}{info}")

        # SYSADMIN required to create warehouses
        self._execute("USE ROLE SYSADMIN")

        if warehouse_type == "adaptive":
            create_sql = (
                f"CREATE ADAPTIVE WAREHOUSE IF NOT EXISTS {warehouse_name}\n"
                f"    MAX_QUERY_PERFORMANCE_LEVEL = '{size_upper}'\n"
                f"    QUERY_THROUGHPUT_MULTIPLIER = {qtm}\n"
                f"    COMMENT = 'Adaptive benchmark warehouse run {self.run_id} "
                f"scenario {scenario} qtm={qtm}'"
            )
        else:
            create_sql = (
                f"CREATE WAREHOUSE IF NOT EXISTS {warehouse_name}\n"
                f"    WITH\n"
                f"    WAREHOUSE_SIZE = '{size_upper}'\n"
                # Pin Gen1 explicitly — Snowflake's default for new warehouses
                # transitioned to Gen2 across most regions in mid-2025.
                f"    GENERATION = '1'\n"
                f"    AUTO_SUSPEND = {WAREHOUSE_AUTO_SUSPEND}\n"
                f"    AUTO_RESUME = {str(WAREHOUSE_AUTO_RESUME).upper()}\n"
                f"    INITIALLY_SUSPENDED = {str(WAREHOUSE_INITIALLY_SUSPENDED).upper()}"
            )
            if max_cluster_count is not None:
                create_sql += f"\n    MAX_CLUSTER_COUNT = {max_cluster_count}"
            if min_cluster_count is not None:
                create_sql += f"\n    MIN_CLUSTER_COUNT = {min_cluster_count}"
            if max_cluster_count is not None:
                create_sql += "\n    SCALING_POLICY = 'STANDARD'"
            create_sql += (
                f"\n    COMMENT = 'Gen1 benchmark warehouse run {self.run_id} "
                f"scenario {scenario}'"
            )

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

        # Gen1 bills an idle tail until AUTO_SUSPEND fires. Adaptive is a
        # query-billed pool with no idle/suspend concept, so only gen1 waits.
        #
        # BENCHMARK_IMMEDIATE_DROP=1 models the opposite "no idle time" policy:
        # drop the warehouse the instant the workload finishes so no idle tail
        # is ever billed. Used to produce the immediate-drop data series
        # alongside the realistic wait-for-suspend series.
        immediate_drop = os.getenv("BENCHMARK_IMMEDIATE_DROP", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if immediate_drop and "_GEN1_" in warehouse_name.upper():
            logger.info(
                f"BENCHMARK_IMMEDIATE_DROP set: dropping {warehouse_name} "
                f"immediately (no idle tail captured)."
            )
        if not immediate_drop and "_GEN1_" in warehouse_name.upper():
            try:
                self._wait_until_suspended(warehouse_name)
            except Exception as e:
                logger.error(f"❌ Wait-for-suspend failed for {warehouse_name}: {e}")

        try:
            drop_sql = f"DROP WAREHOUSE IF EXISTS {warehouse_name}"
            self._execute(drop_sql)
            logger.info(f"✅ Destroyed warehouse: {warehouse_name}")
        except Exception as e:
            logger.error(f"❌ Failed to destroy warehouse {warehouse_name}: {e}")

    def create_all_warehouses(
        self,
        warehouse_sizes: List[str],
        scenario: str,
        warehouse_type: str = "gen1",
        qtm: Optional[int] = None,
        max_cluster_count: int = None,
        min_cluster_count: int = None,
    ) -> Dict[str, str]:
        """
        Create all warehouses needed for this benchmark run.

        Returns dict mapping warehouse_size -> warehouse_name.
        """
        logger.info("\n" + "=" * 70)
        type_label = warehouse_type.upper()
        qtm_label = f" QTM={qtm}" if warehouse_type == "adaptive" and qtm is not None else ""
        logger.info(
            f"CREATING {type_label} WAREHOUSES FOR SCENARIO: {scenario.upper()}{qtm_label}"
        )
        logger.info("=" * 70)

        warehouse_map = {}
        for warehouse_size in warehouse_sizes:
            warehouse_name = self.create_warehouse(
                warehouse_size,
                scenario,
                warehouse_type=warehouse_type,
                qtm=qtm,
                max_cluster_count=max_cluster_count,
                min_cluster_count=min_cluster_count,
            )
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
