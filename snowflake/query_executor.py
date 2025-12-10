#!/usr/bin/env python3
"""
Snowflake Query Executor

Executes TPC-H queries and captures performance metrics.
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
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
            connection: Snowflake connection object
            storage: BenchmarkStorage instance for storing results
            run_id: Run ID for this benchmark
            scale_factor: TPC-H scale factor (e.g., 100, 1000)
        """
        self.connection = connection
        self.storage = storage
        self.run_id = run_id
        self.scale_factor = scale_factor

        # Track warehouse state for run type classification
        # warehouse_name -> {started: bool, queries_executed: Set[int]}
        self.warehouse_states: Dict[str, Dict[str, Any]] = {}

    def _get_warehouse_state(self, warehouse_name: str) -> Dict[str, Any]:
        """
        Get or initialize warehouse state.

        Args:
            warehouse_name: Name of the warehouse

        Returns:
            Dictionary with warehouse state {started: bool, queries_executed: Set[int]}
        """
        if warehouse_name not in self.warehouse_states:
            self.warehouse_states[warehouse_name] = {
                "started": False,
                "queries_executed": set(),
            }
        return self.warehouse_states[warehouse_name]

    def reset_warehouse_state(self, warehouse_name: str):
        """
        Reset state tracking for a warehouse.

        Args:
            warehouse_name: Name of the warehouse
        """
        if warehouse_name in self.warehouse_states:
            del self.warehouse_states[warehouse_name]

    def determine_run_type(
        self, query_num: int, warehouse_name: str, force_run_type: Optional[str] = None
    ) -> str:
        """
        Determine run type (cold/semi-warm/warm) based on warehouse state.

        Args:
            query_num: Query number
            warehouse_name: Name of the warehouse
            force_run_type: If provided, override auto-detection

        Returns:
            Run type: "cold", "semi-warm", or "warm"
        """
        if force_run_type:
            return force_run_type

        state = self._get_warehouse_state(warehouse_name)

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
        Load TPC-H query from file and substitute the scale factor.

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

        # Replace the scale factor in the query (e.g., TPCH_SF100 -> TPCH_SF1000)
        query_sql = query_sql.replace("TPCH_SF100", f"TPCH_SF{self.scale_factor}")

        return query_sql

    def load_ctas_query(self) -> str:
        """
        Load the special CTAS benchmark query from file.

        Returns:
            Query SQL string with scale factor substituted

        Raises:
            FileNotFoundError: If ctas.sql doesn't exist
        """
        query_file = QUERIES_DIR / "ctas.sql"
        if not query_file.exists():
            raise FileNotFoundError(f"CTAS query file not found: {query_file}")

        with open(query_file, "r") as f:
            query_sql = f.read().strip()

        # Replace the scale factor in the query (e.g., TPCH_SF100 -> TPCH_SF1000)
        query_sql = query_sql.replace("TPCH_SF100", f"TPCH_SF{self.scale_factor}")

        return query_sql

    def set_query_tag(self, query_tag: Dict[str, Any]):
        """
        Set the query tag for the next query.

        Args:
            query_tag: Dictionary to be serialized as JSON query tag
        """
        # Serialize the query tag to JSON
        query_tag_json = json.dumps(query_tag)
        # Escape single quotes for SQL by doubling them
        query_tag_escaped = query_tag_json.replace("'", "''")

        cursor = self.connection.cursor()
        cursor.execute(f"ALTER SESSION SET QUERY_TAG = '{query_tag_escaped}'")
        cursor.close()

    def execute_query(
        self,
        query_num: int,
        run_num: int,
        warehouse_name: str,
        warehouse_size: str,
        scenario: str,
        force_run_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a single TPC-H query and capture metrics.

        Args:
            query_num: Query number (1-22)
            run_num: Run iteration (1-4)
            warehouse_name: Name of the warehouse
            warehouse_size: Size of the warehouse (SMALL, MEDIUM, XLARGE)
            scenario: Scenario name (e.g., "normal", "coldstart", "concurrent")
            force_run_type: Optional override for run type detection

        Returns:
            Dictionary with query execution metrics
        """
        # Determine run type based on warehouse state
        run_type = self.determine_run_type(query_num, warehouse_name, force_run_type)

        # Create JSON structured query tag
        query_tag = {
            "app": APP_NAME,
            "workload_id": f"q{query_num:02d}",
            "run_id": self.run_id,
            "scenario": scenario,
        }

        # Include warehouse size in log output for clarity in parallel execution
        platform_prefix = "[SNOWFLAKE]"
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
                warehouse_name,
                warehouse_size,
                scenario,
                str(e),
            )

        # Set query tag
        self.set_query_tag(query_tag)

        # Log query start
        logger.info(f"{log_prefix} 🚀 Starting...")

        # Execute query and measure time
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat()
        error_message = None
        query_id = None
        rows_produced = 0

        try:
            # Execute asynchronously to get query ID immediately
            cursor = self.connection.cursor()
            cursor.execute_async(query_sql)
            query_id = cursor.sfqid

            # Wait for completion
            while self.connection.is_still_running(
                self.connection.get_query_status(query_id)
            ):
                time.sleep(0.5)

            # Don't fetch results - just get row count from query status
            # Fetching large result sets can cause memory issues and conversion errors
            try:
                self.connection.get_query_status_throw_if_error(query_id)
                # Try to get row count from query stats (may not always be available)
                rows_produced = cursor.rowcount if cursor.rowcount >= 0 else -1
            except Exception:
                # If we can't get row count, just use -1
                rows_produced = -1

            cursor.close()

        except Exception as e:
            error_message = str(e)
            logger.error(f"{log_prefix} ❌ Error: {error_message[:50]}")

        execution_time = time.time() - start_time

        if error_message is None:
            # Format row count message
            row_msg = f"({rows_produced:,} rows)" if rows_produced >= 0 else ""
            logger.info(f"{log_prefix} ✅ {execution_time:.2f}s {row_msg}".strip())

            # Update warehouse state
            state = self._get_warehouse_state(warehouse_name)
            state["started"] = True
            state["queries_executed"].add(query_num)

        # Create result record
        result = {
            "run_id": self.run_id,
            "timestamp": timestamp,
            "platform": "snowflake",
            "scenario": scenario,
            "warehouse_name": warehouse_name,
            "warehouse_size": warehouse_size,
            "query_num": query_num,
            "run_num": run_num,
            "run_type": run_type,
            "query_tag": json.dumps(query_tag),  # Store as JSON string
            "query_id": query_id or "",
            "execution_time_sec": round(execution_time, 3),
            "rows_produced": rows_produced,
            "error_message": error_message or "",
        }

        # Log to DuckDB immediately
        self.storage.write_result(result)

        return result

    def _wrap_query_as_ctas(self, query_sql: str, query_num: int) -> str:
        """
        Wrap a SELECT query as CREATE OR REPLACE TABLE AS SELECT.

        Args:
            query_sql: Original SELECT query
            query_num: Query number (for table naming)

        Returns:
            CTAS-wrapped SQL
        """
        table_name = f"BENCHMARK_CTAS_Q{query_num:02d}_{self.run_id}"
        return f"CREATE OR REPLACE TABLE {table_name} AS\n{query_sql}"

    def execute_ctas_query(
        self,
        query_num: int,
        run_num: int,
        warehouse_name: str,
        warehouse_size: str,
        scenario: str,
        force_run_type: Optional[str] = None,
        query_sql: Optional[str] = None,
        table_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a TPC-H query as CREATE TABLE AS SELECT.

        This wraps the query in CREATE OR REPLACE TABLE statement and executes it.
        Metrics are collected the same way as execute_query().

        Args:
            query_num: Query number (1-22, or 0 for special CTAS query)
            run_num: Run iteration (1-4)
            warehouse_name: Name of the warehouse
            warehouse_size: Size of the warehouse (SMALL, MEDIUM, XLARGE)
            scenario: Scenario name (should be "ctas")
            force_run_type: Optional override for run type detection
            query_sql: Optional pre-loaded query SQL (if None, loads from q{query_num}.sql)
            table_name: Optional custom table name (if None, uses BENCHMARK_CTAS_Q{query_num}_{run_id})

        Returns:
            Dictionary with query execution metrics
        """
        # Determine run type based on warehouse state
        run_type = self.determine_run_type(query_num, warehouse_name, force_run_type)

        # Create JSON structured query tag
        workload_id = "ctas" if query_num == 0 else f"q{query_num:02d}"
        query_tag = {
            "app": APP_NAME,
            "workload_id": workload_id,
            "run_id": self.run_id,
            "scenario": scenario,
        }

        # Include warehouse size in log output for clarity
        platform_prefix = "[SNOWFLAKE]"
        wh_prefix = f"[{warehouse_size:6s}]" if warehouse_size else ""
        query_label = "CTAS" if query_num == 0 else f"Query {query_num:2d}"
        log_prefix = f"{platform_prefix} {wh_prefix} [{scenario:10s}] [{run_type:10s}] Run {run_num}/{NUM_RUNS}: {query_label}"

        # Load query SQL if not provided, and wrap as CTAS
        try:
            if query_sql is None:
                query_sql = self.load_query(query_num)
            # Use custom table name or generate one
            if table_name is None:
                table_name = f"BENCHMARK_CTAS_Q{query_num:02d}_{self.run_id}"
            ctas_sql = f"CREATE OR REPLACE TABLE {table_name} AS\n{query_sql}"
        except FileNotFoundError as e:
            logger.error(f"{log_prefix} ❌ Error: {e}")
            return self._create_error_result(
                query_num,
                run_num,
                run_type,
                json.dumps(query_tag),
                warehouse_name,
                warehouse_size,
                scenario,
                str(e),
            )

        # Set query tag
        self.set_query_tag(query_tag)

        # Log query start
        logger.info(f"{log_prefix} 🚀 Starting CTAS...")

        # Execute query and measure time
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat()
        error_message = None
        query_id = None
        rows_produced = 0

        try:
            # Execute asynchronously to get query ID immediately
            cursor = self.connection.cursor()
            cursor.execute_async(ctas_sql)
            query_id = cursor.sfqid

            # Wait for completion
            while self.connection.is_still_running(
                self.connection.get_query_status(query_id)
            ):
                time.sleep(0.5)

            # Check for errors and get row count
            try:
                self.connection.get_query_status_throw_if_error(query_id)
                rows_produced = cursor.rowcount if cursor.rowcount >= 0 else -1
            except Exception:
                rows_produced = -1

            cursor.close()

        except Exception as e:
            error_message = str(e)
            logger.error(f"{log_prefix} ❌ Error: {error_message[:50]}")

        execution_time = time.time() - start_time

        if error_message is None:
            row_msg = f"({rows_produced:,} rows)" if rows_produced >= 0 else ""
            logger.info(f"{log_prefix} ✅ {execution_time:.2f}s {row_msg}".strip())

            # Update warehouse state
            state = self._get_warehouse_state(warehouse_name)
            state["started"] = True
            state["queries_executed"].add(query_num)

        # Create result record
        result = {
            "run_id": self.run_id,
            "timestamp": timestamp,
            "platform": "snowflake",
            "scenario": scenario,
            "warehouse_name": warehouse_name,
            "warehouse_size": warehouse_size,
            "query_num": query_num,
            "run_num": run_num,
            "run_type": run_type,
            "query_tag": json.dumps(query_tag),
            "query_id": query_id or "",
            "execution_time_sec": round(execution_time, 3),
            "rows_produced": rows_produced,
            "error_message": error_message or "",
        }

        # Log to DuckDB immediately
        self.storage.write_result(result)

        return result

    def _create_error_result(
        self,
        query_num: int,
        run_num: int,
        run_type: str,
        query_tag: str,
        warehouse_name: str,
        warehouse_size: str,
        scenario: str,
        error_message: str,
    ) -> Dict[str, Any]:
        """Create a result dictionary for an error case."""
        return {
            "run_id": self.run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "platform": "snowflake",
            "scenario": scenario,
            "warehouse_name": warehouse_name,
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
