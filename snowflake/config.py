"""
Configuration for Snowflake TPC-H Benchmark
"""

from pathlib import Path

# Snowflake connection settings (from CLAUDE.md instructions)
SNOWFLAKE_CONNECTION = "demo"
SNOWFLAKE_ROLE = "BENCHMARK"
SNOWFLAKE_DATABASE = "BENCHMARK"
SNOWFLAKE_SCHEMA = "PUBLIC"

# Warehouse configurations
WAREHOUSES = {
    "small": "BENCHMARK_WH_SMALL",
    "medium": "BENCHMARK_WH_MEDIUM",
    "xlarge": "BENCHMARK_WH_XLARGE",
}

# Test parameters
NUM_RUNS = 4  # 1 cold + 3 warm runs
NUM_QUERIES = 22  # All TPC-H queries
COLD_START_DELAY = 180  # 3 minutes (in seconds) between cold runs

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
    "run_type",  # "cold" or "warm"
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
