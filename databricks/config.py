"""
Configuration for Databricks TPC-H Benchmark
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file automatically
load_dotenv()

# Databricks connection settings (from .env file)
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")

# Database and catalog configuration (from .env file - user-specific)
CATALOG = os.getenv("DATABRICKS_CATALOG")
SCHEMA = os.getenv("DATABRICKS_SCHEMA")

# SQL Warehouse configurations (from .env file - user-specific)
# These are SERVERLESS SQL Warehouses (warehouse_type=PRO with enable_serverless_compute=True)
# This is the correct configuration for fair comparison with Snowflake
WAREHOUSES = {
    "xsmall": os.getenv("DATABRICKS_WAREHOUSE_XSMALL"),
    "small": os.getenv("DATABRICKS_WAREHOUSE_SMALL"),
    "large": os.getenv("DATABRICKS_WAREHOUSE_LARGE"),
}

# Ephemeral Warehouse Configuration (for create/destroy pattern like Snowflake)
WAREHOUSE_PREFIX = "benchmark_dbx"  # Prefix for ephemeral warehouse names
WAREHOUSE_SIZES = ["xsmall", "small", "large"]  # Available warehouse sizes

# Map benchmark size keys to Databricks cluster size strings
WAREHOUSE_SIZE_MAP = {
    "xsmall": "2X-Small",
    "small": "Small",
    "large": "Large",
}

# Warehouse auto-suspend configuration
WAREHOUSE_AUTO_STOP_MINS = 10  # Minimum allowed by Databricks (safety net; warehouses are deleted after run)
WAREHOUSE_MAX_NUM_CLUSTERS = 1  # For serverless warehouses

# Test parameters (matching Snowflake)
NUM_RUNS = 1  # Number of times to run each query (default: 1 for faster benchmarks)
NUM_QUERIES = 22  # All TPC-H queries
SCALE_FACTOR = 1000  # TPC-H scale factor (1000 = 1TB, 10000 = 10TB)

# Run type definitions (for parallel warehouse execution):
# - "cold": First query on a warehouse (warehouse just started/resumed)
# - "semi-warm": Subsequent queries on same warehouse (warehouse running, but this query hasn't run yet)
# - "warm": Re-running the same query (query has already executed on this warehouse)

# Query tagging configuration
# Using comments in SQL for tracking
APP_NAME = "tpchbenchmark"

# Directories
BASE_DIR = Path(__file__).parent
QUERIES_DIR = BASE_DIR / "queries"
RESULTS_DIR = BASE_DIR / "results"

# Ensure results directory exists
RESULTS_DIR.mkdir(exist_ok=True)

# DuckDB database path (in project root)
PROJECT_ROOT = BASE_DIR.parent
DUCKDB_PATH = PROJECT_ROOT / "benchmark_results.duckdb"

# CSV Schema - columns for benchmark results (matching Snowflake structure)
CSV_COLUMNS = [
    "run_id",  # UUID for the entire benchmark run session
    "timestamp",  # ISO 8601 timestamp when query was submitted
    "platform",  # "databricks"
    "scenario",  # "primary" (or "concurrency" in future)
    "warehouse_name",  # Warehouse ID
    "warehouse_size",  # "XSMALL", "SMALL", or "LARGE"
    "query_num",  # 1-22 (TPC-H query number)
    "run_num",  # 1-4 (iteration number)
    "run_type",  # "cold", "semi-warm", or "warm"
    "query_tag",  # JSON structured tag: {"app":"tpchbenchmark","workload_id":"q01","run_id":"uuid"}
    "query_id",  # Databricks statement ID
    "execution_time_sec",  # Total elapsed time (client-side measurement)
    "rows_produced",  # Number of rows returned
    "error_message",  # Any error that occurred (empty if successful)
]
