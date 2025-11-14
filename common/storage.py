"""
DuckDB storage layer for benchmark results.

This module provides thread-safe DuckDB storage for benchmark results from both
Snowflake and Databricks benchmarks.
"""

import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional
import duckdb

logger = logging.getLogger(__name__)


class BenchmarkStorage:
    """
    Thread-safe DuckDB storage for benchmark results.

    Creates and manages:
    - snowflake_results table for Snowflake benchmark data
    - databricks_results table for Databricks benchmark data (future)
    - latest_run view that shows the most recent benchmark run
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

    def _init_database(self):
        """Initialize database tables and views if they don't exist."""
        with self.lock:
            conn = duckdb.connect(str(self.db_path))
            try:
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

                # Create latest_run view
                conn.execute("""
                    CREATE OR REPLACE VIEW latest_run AS
                    SELECT *
                    FROM snowflake_results
                    WHERE run_id = (
                        SELECT run_id
                        FROM snowflake_results
                        ORDER BY timestamp DESC
                        LIMIT 1
                    )
                    ORDER BY timestamp
                """)

                conn.commit()
                logger.info(f"Initialized DuckDB database at {self.db_path}")
            finally:
                conn.close()

    def write_result(self, result: Dict[str, Any]):
        """
        Write a single benchmark result to the database.

        Args:
            result: Dictionary containing benchmark result data with keys matching
                   the table schema (run_id, timestamp, platform, etc.)
        """
        with self.lock:
            conn = duckdb.connect(str(self.db_path))
            try:
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
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to write result to DuckDB: {e}")
                raise
            finally:
                conn.close()

    def write_databricks_result(self, result: Dict[str, Any]):
        """
        Write a single Databricks benchmark result to the database.

        Args:
            result: Dictionary containing benchmark result data with keys matching
                   the databricks_results table schema (run_id, timestamp, platform, etc.)
        """
        with self.lock:
            conn = duckdb.connect(str(self.db_path))
            try:
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
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to write Databricks result to DuckDB: {e}")
                raise
            finally:
                conn.close()

    def get_latest_run_id(self) -> Optional[str]:
        """
        Get the run_id of the most recent benchmark run.

        Returns:
            The most recent run_id, or None if no results exist
        """
        with self.lock:
            conn = duckdb.connect(str(self.db_path))
            try:
                result = conn.execute("""
                    SELECT run_id
                    FROM snowflake_results
                    ORDER BY timestamp DESC
                    LIMIT 1
                """).fetchone()
                return result[0] if result else None
            finally:
                conn.close()

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
        with self.lock:
            conn = duckdb.connect(str(self.db_path))
            try:
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
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to update enrichment data for query {query_id}: {e}")
                raise
            finally:
                conn.close()

    def query(self, sql: str) -> list:
        """
        Execute a SQL query against the database.

        Args:
            sql: SQL query to execute

        Returns:
            List of rows from the query result
        """
        with self.lock:
            conn = duckdb.connect(str(self.db_path))
            try:
                return conn.execute(sql).fetchall()
            finally:
                conn.close()
