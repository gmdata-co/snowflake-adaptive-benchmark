#!/usr/bin/env python3
"""
Databricks Query Executor

Executes TPC-H queries and captures performance metrics.
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID
from common.logging_config import get_logger
from common.storage import BenchmarkStorage
from .config import QUERIES_DIR, APP_NAME, NUM_RUNS

logger = get_logger(__name__)


class QueryExecutor:
    """Executes TPC-H queries and captures performance metrics."""

    def __init__(
        self,
        connection,
        storage: BenchmarkStorage,
        run_id: str,
        scale_factor: int,
    ):
        """
        Initialize query executor.

        Args:
            connection: Databricks SQL connection object
            storage: BenchmarkStorage instance for storing results
            run_id: Run ID for this benchmark
            scale_factor: TPC-H scale factor (e.g., 100, 1000)
        """
        self.connection = connection
        self.storage = storage
        self.run_id = run_id
        self.scale_factor = scale_factor

        # Track warehouse state for run type classification
        # warehouse_id -> {started: bool, queries_executed: Set[int]}
        self.warehouse_states: Dict[str, Dict[str, Any]] = {}

    def _get_warehouse_state(self, warehouse_id: str) -> Dict[str, Any]:
        """
        Get or initialize warehouse state.

        Args:
            warehouse_id: ID of the warehouse

        Returns:
            Dictionary with warehouse state {started: bool, queries_executed: Set[int]}
        """
        if warehouse_id not in self.warehouse_states:
            self.warehouse_states[warehouse_id] = {
                "started": False,
                "queries_executed": set(),
            }
        return self.warehouse_states[warehouse_id]

    def reset_warehouse_state(self, warehouse_id: str):
        """
        Reset state tracking for a warehouse.

        Args:
            warehouse_id: ID of the warehouse
        """
        if warehouse_id in self.warehouse_states:
            del self.warehouse_states[warehouse_id]

    def determine_run_type(
        self, query_num: int, warehouse_id: str, force_run_type: Optional[str] = None
    ) -> str:
        """
        Determine run type (cold/semi-warm/warm) based on warehouse state.

        Args:
            query_num: Query number
            warehouse_id: ID of the warehouse
            force_run_type: If provided, override auto-detection

        Returns:
            Run type: "cold", "semi-warm", or "warm"
        """
        if force_run_type:
            return force_run_type

        state = self._get_warehouse_state(warehouse_id)

        if not state["started"]:
            # First query on this warehouse = cold
            return "cold"
        elif query_num not in state["queries_executed"]:
            # Warehouse is running, but this query hasn't run yet = semi-warm
            return "semi-warm"
        else:
            # This query has already run on this warehouse = warm
            return "warm"

    def load_query(self, query_num: int) -> str:
        """
        Load TPC-H query from file.

        Args:
            query_num: Query number (1-22)

        Returns:
            Query SQL string

        Raises:
            FileNotFoundError: If query file doesn't exist
        """
        query_file = QUERIES_DIR / f"q{query_num:02d}.sql"
        if not query_file.exists():
            raise FileNotFoundError(f"Query file not found: {query_file}")

        with open(query_file, "r") as f:
            query_sql = f.read().strip()

        return query_sql

    def execute_query(
        self,
        query_num: int,
        run_num: int,
        warehouse_id: str,
        warehouse_size: str,
        scenario: str,
        force_run_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a single TPC-H query and capture metrics.

        Args:
            query_num: Query number (1-22)
            run_num: Run iteration (1-4)
            warehouse_id: ID of the warehouse
            warehouse_size: Size of the warehouse (XSMALL, SMALL, LARGE)
            scenario: Scenario name (e.g., "normal", "coldstart", "concurrent")
            force_run_type: Optional override for run type detection

        Returns:
            Dictionary with query execution metrics
        """
        # Determine run type based on warehouse state
        run_type = self.determine_run_type(query_num, warehouse_id, force_run_type)

        # Create JSON structured query tag
        query_tag = {
            "app": APP_NAME,
            "workload_id": f"q{query_num:02d}",
            "run_id": self.run_id,
            "scenario": scenario,
        }

        # Include warehouse size in log output for clarity in parallel execution
        platform_prefix = "[DATABRICKS]"
        wh_prefix = f"[{warehouse_size:6s}]" if warehouse_size else ""
        log_prefix = f"{platform_prefix} {wh_prefix} [{scenario:10s}] [{run_type:10s}] Run {run_num}/{NUM_RUNS}: Query {query_num:2d}"

        # Load query SQL
        try:
            query_sql = self.load_query(query_num)
        except FileNotFoundError as e:
            logger.error(f"{log_prefix} ❌ Error: {e}")
            return self._create_error_result(
                query_num,
                run_num,
                run_type,
                json.dumps(query_tag),
                warehouse_id,
                warehouse_size,
                scenario,
                str(e),
            )

        # Add query tag as SQL comment
        query_tag_json = json.dumps(query_tag)
        tagged_query = f"/* BENCHMARK: {query_tag_json} */\n{query_sql}"

        # Log query start
        logger.info(f"{log_prefix} 🚀 Starting...")

        # Execute query and measure time
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat()
        error_message = None
        statement_id = None
        rows_produced = 0

        try:
            # Execute query
            cursor = self.connection.cursor()
            cursor.execute(tagged_query)

            # Get statement_id from cursor
            # Reference: https://stackoverflow.com/questions/77961077/
            try:
                if (
                    hasattr(cursor, "active_op_handle")
                    and cursor.active_op_handle is not None
                ):
                    if hasattr(cursor.active_op_handle, "operationId"):
                        # Convert GUID bytes to UUID string
                        guid_bytes = cursor.active_op_handle.operationId.guid
                        statement_id = str(UUID(bytes=guid_bytes))
                        logger.debug(f"{log_prefix} Captured statement_id: {statement_id}")
            except Exception as e:
                # If we can't get the statement_id, log warning but continue
                logger.warning(f"{log_prefix} Failed to capture statement_id: {e}")

            # Close cursor immediately - don't fetch results for benchmarking
            # We only care about query execution time, not data transfer time
            cursor.close()

            # Row count not available (not fetching results)
            rows_produced = -1

        except Exception as e:
            error_message = str(e)
            logger.error(f"{log_prefix} ❌ Error: {error_message[:50]}")

        execution_time = time.time() - start_time

        if error_message is None:
            logger.info(f"{log_prefix} ✅ {execution_time:.2f}s")

            # Update warehouse state
            state = self._get_warehouse_state(warehouse_id)
            state["started"] = True
            state["queries_executed"].add(query_num)

        # Create result record
        result = {
            "run_id": self.run_id,
            "timestamp": timestamp,
            "platform": "databricks",
            "scenario": scenario,
            "warehouse_name": warehouse_id,
            "warehouse_size": warehouse_size,
            "query_num": query_num,
            "run_num": run_num,
            "run_type": run_type,
            "query_tag": json.dumps(query_tag),  # Store as JSON string
            "query_id": statement_id or "",
            "execution_time_sec": round(execution_time, 3),
            "rows_produced": rows_produced,
            "error_message": error_message or "",
        }

        # Log to DuckDB immediately
        self.storage.write_databricks_result(result)

        return result

    def _create_error_result(
        self,
        query_num: int,
        run_num: int,
        run_type: str,
        query_tag: str,
        warehouse_id: str,
        warehouse_size: str,
        scenario: str,
        error_message: str,
    ) -> Dict[str, Any]:
        """Create a result dictionary for an error case."""
        return {
            "run_id": self.run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "platform": "databricks",
            "scenario": scenario,
            "warehouse_name": warehouse_id,
            "warehouse_size": warehouse_size,
            "query_num": query_num,
            "run_num": run_num,
            "run_type": run_type,
            "query_tag": query_tag,
            "query_id": "",
            "execution_time_sec": 0.0,
            "rows_produced": 0,
            "error_message": error_message,
        }
