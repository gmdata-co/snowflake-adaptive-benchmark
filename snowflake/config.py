"""
Configuration for Snowflake TPC-H Benchmark
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file automatically
load_dotenv()

# Snowflake connection settings (from .env file)
SNOWFLAKE_CONNECTION = os.getenv("SNOWFLAKE_CONNECTION")

# Snowflake database objects (from .env file - user-specific)
SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")

# Fully-qualified target table for the DML scenario. The DML SQL files use the
# {{DML_TABLE}} placeholder; query_executor substitutes this value. The DB and
# schema are auto-created by _setup_dml_table() if missing.
DML_TABLE = f"{SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.LINEITEM_DML"

# Warehouse configurations
# Warehouses are created dynamically per benchmark run with run_id suffix
# e.g., {SNOWFLAKE_WAREHOUSE_PREFIX}_{TYPE}_{SIZE}_{SCENARIO}[_QTM{n}]_{RUN_ID}
WAREHOUSE_SIZES = ["xsmall", "small", "medium", "large", "xlarge"]
WAREHOUSE_SIZE_MAP = {
    "xsmall": "XSMALL",
    "small": "SMALL",
    "medium": "MEDIUM",
    "large": "LARGE",
    "xlarge": "XLARGE",
}

# Warehouse type: "gen1" (legacy standard, pin GENERATION='1') vs
# "adaptive" (CREATE ADAPTIVE WAREHOUSE with MAX_QUERY_PERFORMANCE_LEVEL + QTM).
# Note: Snowflake's new default for CREATE WAREHOUSE is Gen2 in most regions
# (rollout 2025-06/07), so gen1 must be explicitly pinned to keep a stable baseline.
WAREHOUSE_TYPES = ["gen1", "adaptive"]

# QUERY_THROUGHPUT_MULTIPLIER (QTM) — adaptive warehouses only.
# Snowflake default is 2. Higher values let the adaptive pool serve more
# concurrent queries before queueing. Ignored for gen1.
DEFAULT_QTM = 2

def resolve_idle_policy(warehouse_type: str) -> str:
    """
    The warehouse idle/shutdown policy for a given warehouse type, decided AT
    RUN TIME (recorded as a real column, never guessed later by run_id).

    - adaptive: 'n_a' — per-query billed, no idle/suspend concept; the policy
      toggle does not apply, so adaptive shows identically under both states.
    - gen1: 'immediate_drop' when BENCHMARK_IMMEDIATE_DROP is truthy (warehouse
      killed the instant the workload finishes — no idle tail), otherwise
      'wait_for_suspend' (left to AUTO_SUSPEND before drop — idle tail billed).
    """
    if warehouse_type == "adaptive":
        return "n_a"
    immediate = os.getenv("BENCHMARK_IMMEDIATE_DROP", "").strip().lower() in (
        "1", "true", "yes",
    )
    return "immediate_drop" if immediate else "wait_for_suspend"


WAREHOUSE_PREFIX = os.getenv("SNOWFLAKE_WAREHOUSE_PREFIX", "BENCHMARK_WH")
ADMIN_WAREHOUSE = os.getenv("SNOWFLAKE_ADMIN_WAREHOUSE", "COMPUTE_WH")

# Warehouse settings for dynamic creation (gen1 only — adaptive ignores these)
WAREHOUSE_AUTO_SUSPEND = 60  # 1 min — gen1 idle tail until suspend is real-world cost
WAREHOUSE_AUTO_RESUME = True
WAREHOUSE_INITIALLY_SUSPENDED = True

# Test parameters
NUM_RUNS = 1  # Number of times to run each query (default: 1 for faster benchmarks)
NUM_QUERIES = 22  # All TPC-H queries
SCALE_FACTOR = 100  # TPC-H scale factor: SF100 = ~600M LINEITEM rows

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

# DuckDB database path (in project root)
PROJECT_ROOT = BASE_DIR.parent
# Overridable so 3 benchmark tracks (adaptive / gen1 wait-for-suspend /
# gen1 immediate-drop) can run concurrently, each writing its OWN duckdb
# file (DuckDB is single-writer). The 3 track DBs are merged into the
# canonical PROJECT_ROOT/benchmark_results.duckdb afterwards. enrich /
# dbt / update_data run with the env UNSET so they hit the canonical DB.
DUCKDB_PATH = Path(
    os.getenv("BENCHMARK_DUCKDB_PATH", str(PROJECT_ROOT / "benchmark_results.duckdb"))
)

# CSV Schema - columns for benchmark results
CSV_COLUMNS = [
    "run_id",  # UUID for the entire benchmark run session
    "timestamp",  # ISO 8601 timestamp when query was submitted
    "platform",  # "snowflake" (for future comparison with databricks)
    "scenario",  # "sequential", "concurrent", "dml"
    "warehouse_type",  # "gen1" or "adaptive"
    "warehouse_name",  # e.g., "BENCHMARK_WH_ADAPTIVE_MEDIUM_SEQUENTIAL_QTM2_<RUN_ID>"
    "warehouse_size",  # "SMALL", "MEDIUM", "LARGE", or "XLARGE"
    "qtm",  # QUERY_THROUGHPUT_MULTIPLIER (adaptive only; NULL for gen1)
    "query_num",  # 1-22 (TPC-H query number)
    "run_num",  # 1-4 (iteration number)
    "run_type",  # "cold", "semi-warm", or "warm" (see below for definitions)
    "query_tag",  # JSON structured tag: {"app":"tpchbenchmark","workload_id":"q01","run_id":"uuid"}
    "query_id",  # Snowflake query ID (sfqid)
    "execution_time_sec",  # Total elapsed time (client-side measurement)
    "rows_produced",  # Number of rows returned
    "error_message",  # Any error that occurred (empty if successful)
]

# Account Usage query delay — adaptive billing may take longer to settle than legacy.
ACCOUNT_USAGE_DELAY_MINUTES = 90

# Enriched CSV columns (additional fields from ACCOUNT_USAGE.QUERY_HISTORY
# and WAREHOUSE_METERING_HISTORY).
# For gen1: credits_used_compute is allocated proportionally by elapsed time
# from WAREHOUSE_METERING_HISTORY across queries on that warehouse.
# For adaptive: credits_used_compute comes from per-query attribution in
# QUERY_HISTORY (adaptive uses query-based billing).
ENRICHED_CSV_COLUMNS = CSV_COLUMNS + [
    "compilation_time_ms",
    "queued_time_ms",
    "bytes_scanned",
    "credits_used_compute",
    "credits_used_cloud_services",
    "total_elapsed_time_ms",
]
