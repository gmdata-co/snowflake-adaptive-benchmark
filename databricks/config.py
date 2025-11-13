"""
Configuration for Databricks TPC-H Benchmark
"""

from pathlib import Path

# Databricks connection settings
# These will be loaded from ~/.databrickscfg or environment variables
DATABRICKS_PROFILE = "DEFAULT"  # Connection profile name

# SQL Warehouse configurations
# Created by project_setup.py
WAREHOUSES = {
    "xsmall": "f9de55834a86c9db",  # SMALL equivalent (2X-Small)
    "small": "81c01fce5f1c223c",  # MEDIUM equivalent (Small) - Primary baseline
    "large": "e2ce84a538ff2ada",  # X-LARGE equivalent (Large)
}

# Test parameters (matching Snowflake)
NUM_RUNS = 4  # Number of times to run each query
NUM_QUERIES = 22  # All TPC-H queries
SCALE_FACTOR = 1000  # TPC-H scale factor (100 = 100GB, 1000 = 1TB)

# Database and catalog configuration
# Created by project_setup.py
CATALOG = "select_pathfinder"
SCHEMA = "benchmark"  # Schema for TPC-H tables (scale factor agnostic)

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
