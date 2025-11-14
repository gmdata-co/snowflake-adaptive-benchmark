"""
Configuration for Snowflake TPC-H Benchmark
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file automatically
load_dotenv()

# Snowflake connection settings (from .env file via SNOWFLAKE_CONNECTION environment variable)
SNOWFLAKE_CONNECTION = os.getenv("SNOWFLAKE_CONNECTION")
SNOWFLAKE_ROLE = "BENCHMARK"
SNOWFLAKE_DATABASE = "BENCHMARK"
SNOWFLAKE_SCHEMA = "PUBLIC"

# Warehouse configurations
# Warehouses are created dynamically per benchmark run with run_id suffix
# e.g., BENCHMARK_WH_MEDIUM_001 for run_id 001
WAREHOUSE_SIZES = ["small", "medium", "xlarge"]
WAREHOUSE_SIZE_MAP = {
    "small": "SMALL",
    "medium": "MEDIUM",
    "xlarge": "XLARGE",
}
WAREHOUSE_PREFIX = "BENCHMARK_WH"

# Warehouse settings for dynamic creation
WAREHOUSE_AUTO_SUSPEND = 120  # 2 minutes
WAREHOUSE_AUTO_RESUME = True
WAREHOUSE_INITIALLY_SUSPENDED = True

# Test parameters
NUM_RUNS = 4  # Number of times to run each query
NUM_QUERIES = 22  # All TPC-H queries
SCALE_FACTOR = 1000  # TPC-H scale factor (100 = 100GB, 1000 = 1TB)

# Run type definitions (for parallel warehouse execution):
# - "cold": First query on a warehouse (warehouse just started/resumed)
# - "semi-warm": Subsequent queries on same warehouse (warehouse running, but this query hasn't run yet)
# - "warm": Re-running the same query (query has already executed on this warehouse)

# Query tagging configuration
# Using JSON structured tags for better queryability
APP_NAME = "tpchbenchmark"

# Directories
BASE_DIR = Path(__file__).parent
QUERIES_DIR = BASE_DIR / "queries" / "adapted_queries"
RESULTS_DIR = BASE_DIR / "results"

# Ensure results directory exists
RESULTS_DIR.mkdir(exist_ok=True)

# CSV Schema - columns for benchmark results
CSV_COLUMNS = [
    "run_id",  # UUID for the entire benchmark run session
    "timestamp",  # ISO 8601 timestamp when query was submitted
    "platform",  # "snowflake" (for future comparison with databricks)
    "scenario",  # "primary" (or "concurrency" in future)
    "warehouse_name",  # e.g., "BENCHMARK_WH_MEDIUM"
    "warehouse_size",  # "SMALL", "MEDIUM", or "XLARGE"
    "query_num",  # 1-22 (TPC-H query number)
    "run_num",  # 1-4 (iteration number)
    "run_type",  # "cold", "semi-warm", or "warm" (see below for definitions)
    "query_tag",  # JSON structured tag: {"app":"tpchbenchmark","workload_id":"q01","run_id":"uuid"}
    "query_id",  # Snowflake query ID (sfqid)
    "execution_time_sec",  # Total elapsed time (client-side measurement)
    "rows_produced",  # Number of rows returned
    "error_message",  # Any error that occurred (empty if successful)
]

# Account Usage query delay (from project_plan.md)
ACCOUNT_USAGE_DELAY_MINUTES = 45

# Enriched CSV columns (additional fields from ACCOUNT_USAGE.QUERY_HISTORY)
ENRICHED_CSV_COLUMNS = CSV_COLUMNS + [
    "compilation_time_ms",
    "queued_time_ms",
    "bytes_scanned",
    "credits_used_compute",
    "credits_used_cloud_services",
    "total_elapsed_time_ms",
]
