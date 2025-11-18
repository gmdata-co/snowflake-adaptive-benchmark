"""
DuckDB storage layer for benchmark results.

This module provides thread-safe DuckDB storage for benchmark results from both
Snowflake and Databricks benchmarks.
"""

import threading
from pathlib import Path
from typing import Dict, Any, Optional
import duckdb

# Initialize centralized logging
from .logging_config import get_logger

logger = get_logger(__name__)


def _is_lock_error(exception: Exception) -> bool:
    """
    Check if an exception is a DuckDB lock error.

    Args:
        exception: The exception to check

    Returns:
        True if the exception is a lock error, False otherwise
    """
    error_msg = str(exception).lower()
    return (
        isinstance(exception, duckdb.IOException) and
        ("could not set lock" in error_msg or "database is locked" in error_msg)
    )


def _prompt_user_to_unlock():
    """
    Prompt the user to close DuckDB connections and press Enter to retry.
    """
    print("\n" + "=" * 70)
    print("⚠️  DuckDB DATABASE IS LOCKED")
    print("=" * 70)
    print("The database file is currently locked by another process.")
    print("This is likely because:")
    print("  - DBeaver or another database tool has the file open")
    print("  - Another benchmark process is running")
    print("  - A previous process crashed without closing the connection")
    print()
    print("Please close all connections to the database and press Enter to retry...")
    print("(or press Ctrl+C to cancel)")
    print("=" * 70)
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        raise


class BenchmarkStorage:
    """
    Thread-safe DuckDB storage for benchmark results.

    Creates and manages:
    - snowflake_results table for Snowflake benchmark data
    - databricks_results table for Databricks benchmark data

    Note: Views for latest runs and comparisons are managed via SQL files
    in common/transformations/ - run common/run_transformations.sh to create them.
    """

    def __init__(self, db_path: Path):
        """
        Initialize DuckDB storage.

        Args:
            db_path: Path to the DuckDB database file
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()

    def _execute_with_lock_retry(self, operation_name: str, operation_func):
        """
        Execute a DuckDB operation with automatic retry on lock errors.

        This method wraps DuckDB operations and handles the case where the database
        file is locked by another process (e.g., DBeaver, another benchmark).

        Args:
            operation_name: Human-readable name of the operation (for logging)
            operation_func: Callable that performs the DuckDB operation.
                          Should accept a connection object and return the result.

        Returns:
            The result from operation_func

        Raises:
            KeyboardInterrupt: If user cancels during lock retry
            Exception: Any non-lock exception from the operation
        """
        while True:
            conn = None
            is_lock_error = False

            with self.lock:
                try:
                    conn = duckdb.connect(str(self.db_path))
                    result = operation_func(conn)
                    conn.commit()
                    return result
                except Exception as e:
                    if _is_lock_error(e):
                        is_lock_error = True
                        logger.warning(f"DuckDB lock detected during {operation_name}")
                    else:
                        logger.error(f"Failed to {operation_name}: {e}")
                        raise
                finally:
                    if conn is not None:
                        conn.close()

            # If we detected a lock error, prompt user and retry
            if is_lock_error:
                _prompt_user_to_unlock()
            else:
                # Should not reach here, but break just in case
                break

    def _init_database(self):
        """Initialize database tables and views if they don't exist."""
        def _init_operation(conn):
            # Create snowflake_results table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snowflake_results (
                    run_id VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    platform VARCHAR NOT NULL,
                    scenario VARCHAR NOT NULL,
                    warehouse_name VARCHAR NOT NULL,
                    warehouse_size VARCHAR NOT NULL,
                    query_num INTEGER NOT NULL,
                    run_num INTEGER NOT NULL,
                    run_type VARCHAR NOT NULL,
                    query_tag VARCHAR,
                    query_id VARCHAR,
                    execution_time_sec DOUBLE,
                    rows_produced BIGINT,
                    error_message VARCHAR,
                    -- Enriched columns (populated later by enrich_results.py)
                    compilation_time_ms DOUBLE,
                    queued_time_ms DOUBLE,
                    bytes_scanned BIGINT,
                    credits_used_compute DOUBLE,
                    credits_used_cloud_services DOUBLE,
                    total_elapsed_time_ms DOUBLE
                )
            """)

            # Create databricks_results table (same schema as snowflake_results)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS databricks_results (
                    run_id VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    platform VARCHAR NOT NULL,
                    scenario VARCHAR NOT NULL,
                    warehouse_name VARCHAR NOT NULL,
                    warehouse_size VARCHAR NOT NULL,
                    query_num INTEGER NOT NULL,
                    run_num INTEGER NOT NULL,
                    run_type VARCHAR NOT NULL,
                    query_tag VARCHAR,
                    query_id VARCHAR,
                    execution_time_sec DOUBLE,
                    rows_produced BIGINT,
                    error_message VARCHAR,
                    -- Enriched columns (populated later if needed)
                    compilation_time_ms DOUBLE,
                    queued_time_ms DOUBLE,
                    bytes_scanned BIGINT,
                    credits_used_compute DOUBLE,
                    credits_used_cloud_services DOUBLE,
                    total_elapsed_time_ms DOUBLE
                )
            """)

            logger.info(f"Initialized DuckDB database at {self.db_path}")
            return None

        self._execute_with_lock_retry("initialize database", _init_operation)

    def write_result(self, result: Dict[str, Any]):
        """
        Write a single benchmark result to the database.

        Args:
            result: Dictionary containing benchmark result data with keys matching
                   the table schema (run_id, timestamp, platform, etc.)
        """
        def _write_operation(conn):
            # Insert the result
            conn.execute("""
                INSERT INTO snowflake_results (
                    run_id, timestamp, platform, scenario,
                    warehouse_name, warehouse_size, query_num, run_num,
                    run_type, query_tag, query_id, execution_time_sec,
                    rows_produced, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                result.get("run_id"),
                result.get("timestamp"),
                result.get("platform"),
                result.get("scenario"),
                result.get("warehouse_name"),
                result.get("warehouse_size"),
                result.get("query_num"),
                result.get("run_num"),
                result.get("run_type"),
                result.get("query_tag"),
                result.get("query_id"),
                result.get("execution_time_sec"),
                result.get("rows_produced"),
                result.get("error_message"),
            ])
            return None

        self._execute_with_lock_retry("write Snowflake result", _write_operation)

    def write_databricks_result(self, result: Dict[str, Any]):
        """
        Write a single Databricks benchmark result to the database.

        Args:
            result: Dictionary containing benchmark result data with keys matching
                   the databricks_results table schema (run_id, timestamp, platform, etc.)
        """
        def _write_operation(conn):
            # Insert the result
            conn.execute("""
                INSERT INTO databricks_results (
                    run_id, timestamp, platform, scenario,
                    warehouse_name, warehouse_size, query_num, run_num,
                    run_type, query_tag, query_id, execution_time_sec,
                    rows_produced, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                result.get("run_id"),
                result.get("timestamp"),
                result.get("platform"),
                result.get("scenario"),
                result.get("warehouse_name"),
                result.get("warehouse_size"),
                result.get("query_num"),
                result.get("run_num"),
                result.get("run_type"),
                result.get("query_tag"),
                result.get("query_id"),
                result.get("execution_time_sec"),
                result.get("rows_produced"),
                result.get("error_message"),
            ])
            return None

        self._execute_with_lock_retry("write Databricks result", _write_operation)

    def get_latest_run_id(self) -> Optional[str]:
        """
        Get the run_id of the most recent benchmark run.

        Returns:
            The most recent run_id, or None if no results exist
        """
        def _get_operation(conn):
            result = conn.execute("""
                SELECT run_id
                FROM snowflake_results
                ORDER BY timestamp DESC
                LIMIT 1
            """).fetchone()
            return result[0] if result else None

        return self._execute_with_lock_retry("get latest run_id", _get_operation)

    def update_enrichment_data(
        self,
        query_id: str,
        compilation_time_ms: Optional[float] = None,
        queued_time_ms: Optional[float] = None,
        bytes_scanned: Optional[int] = None,
        credits_used_compute: Optional[float] = None,
        credits_used_cloud_services: Optional[float] = None,
        total_elapsed_time_ms: Optional[float] = None,
    ):
        """
        Update enrichment data for a specific query.

        This is called by enrich_results.py to add ACCOUNT_USAGE data.

        Args:
            query_id: Snowflake query ID to update
            compilation_time_ms: Query compilation time
            queued_time_ms: Time spent queued
            bytes_scanned: Total bytes scanned
            credits_used_compute: Compute credits used
            credits_used_cloud_services: Cloud services credits used
            total_elapsed_time_ms: Total elapsed time from ACCOUNT_USAGE
        """
        def _update_operation(conn):
            conn.execute("""
                UPDATE snowflake_results
                SET
                    compilation_time_ms = ?,
                    queued_time_ms = ?,
                    bytes_scanned = ?,
                    credits_used_compute = ?,
                    credits_used_cloud_services = ?,
                    total_elapsed_time_ms = ?
                WHERE query_id = ?
            """, [
                compilation_time_ms,
                queued_time_ms,
                bytes_scanned,
                credits_used_compute,
                credits_used_cloud_services,
                total_elapsed_time_ms,
                query_id,
            ])
            return None

        self._execute_with_lock_retry("update Snowflake enrichment data", _update_operation)

    def update_databricks_enrichment_data(
        self,
        query_id: str,
        compilation_time_ms: Optional[float] = None,
        queued_time_ms: Optional[float] = None,
        bytes_scanned: Optional[int] = None,
        credits_used_compute: Optional[float] = None,
        credits_used_cloud_services: Optional[float] = None,
        total_elapsed_time_ms: Optional[float] = None,
        rows_produced: Optional[int] = None,
    ):
        """
        Update enrichment data for a specific Databricks query.

        This is called by databricks/enrich_results.py to add system table data.

        Args:
            query_id: Databricks statement ID to update
            compilation_time_ms: Query compilation time
            queued_time_ms: Time spent queued
            bytes_scanned: Total bytes scanned
            credits_used_compute: DBU credits used (approximate)
            credits_used_cloud_services: Cloud services credits used (if applicable)
            total_elapsed_time_ms: Total elapsed time from system tables
            rows_produced: Number of rows produced by the query (from system.query.history)
        """
        def _update_operation(conn):
            conn.execute("""
                UPDATE databricks_results
                SET
                    compilation_time_ms = ?,
                    queued_time_ms = ?,
                    bytes_scanned = ?,
                    credits_used_compute = ?,
                    credits_used_cloud_services = ?,
                    total_elapsed_time_ms = ?,
                    rows_produced = ?
                WHERE query_id = ?
            """, [
                compilation_time_ms,
                queued_time_ms,
                bytes_scanned,
                credits_used_compute,
                credits_used_cloud_services,
                total_elapsed_time_ms,
                rows_produced,
                query_id,
            ])
            return None

        self._execute_with_lock_retry("update Databricks enrichment data", _update_operation)

    def query(self, sql: str) -> list:
        """
        Execute a SQL query against the database.

        Args:
            sql: SQL query to execute

        Returns:
            List of rows from the query result
        """
        def _query_operation(conn):
            return conn.execute(sql).fetchall()

        return self._execute_with_lock_retry("query database", _query_operation)
