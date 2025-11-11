# Snowflake TPC-H Benchmark

This directory contains the Snowflake benchmarking setup for the TPC-H SF100 (100GB) dataset for comparison against Databricks.

## Overview

The benchmark executes all 22 TPC-H queries against Snowflake warehouses and logs detailed performance metrics for analysis and comparison.

## Prerequisites

1. **Snowflake Account** with access to `SNOWFLAKE_SAMPLE_DATA.TPCH_SF100`
2. **Snowflake CLI** configured with a connection named `demo` (or customize in config.py)
3. **Python 3.11+** with `uv` package manager
4. **Benchmark Setup** completed (warehouses and role created)

## Project Structure

```
snowflake/
├── README.md                 # This file
├── config.py                 # Configuration constants
├── benchmark.py              # Main benchmark execution script
├── enrich_results.py         # Post-run enrichment from ACCOUNT_USAGE
├── adapt_queries.py          # Query adaptation script (already run)
├── project_setup.sql         # Snowflake setup SQL
├── queries/                  # TPC-H queries (q01.sql - q22.sql)
│   ├── q01.sql
│   ├── q02.sql
│   └── ...
└── results/                  # Benchmark results
    └── benchmark_results.csv # Single CSV with all benchmark runs
```

## Setup

### 1. Create Snowflake Resources

Run the project setup to create the necessary role, database, and warehouses:

```bash
snow sql --connection demo -f snowflake/project_setup.sql
```

This creates:
- **Role**: `BENCHMARK`
- **Database**: `BENCHMARK`
- **Warehouses**:
  - `BENCHMARK_WH_SMALL` (SMALL size)
  - `BENCHMARK_WH_MEDIUM` (MEDIUM size)
  - `BENCHMARK_WH_XLARGE` (X-LARGE size)

All warehouses have a 2-minute auto-suspend timeout.

### 2. Install Dependencies

Dependencies are already installed via uv if you've set up the project:

```bash
# From project root
uv sync
```

## Running the Benchmark

### Basic Usage

Run the complete benchmark (all 22 queries, 4 runs each, all warehouse sizes):

```bash
uv run snowflake/benchmark.py
```

This will take several hours to complete.

### Customize Benchmark Run

#### Test a Single Warehouse

```bash
uv run snowflake/benchmark.py --warehouse medium
```

#### Test Specific Queries

```bash
# Run only queries 1, 3, and 5
uv run snowflake/benchmark.py --queries "1,3,5"

# Run only query 1 (for testing)
uv run snowflake/benchmark.py --queries "1"
```

#### Adjust Number of Runs

```bash
# Run only 2 iterations per query (1 cold + 1 warm)
uv run snowflake/benchmark.py --runs 2
```

#### Combine Options

```bash
# Test query 1 on medium warehouse with 2 runs
uv run snowflake/benchmark.py --warehouse medium --queries "1" --runs 2
```

### Command-Line Options

```
--warehouse {small,medium,xlarge}
    Warehouse size(s) to test (can specify multiple times)
    Default: all three sizes

--queries "1,3,5,..."
    Comma-separated list of query numbers to run
    Default: all 22 queries (1-22)

--runs N
    Number of runs per query
    Default: 4 (1 cold + 3 warm runs)

--connection NAME
    Snowflake connection name from ~/.snowflake/connections.toml
    Default: demo
```

## Understanding the Results

### Benchmark Results File

All benchmark runs are logged to a single CSV file at `snowflake/results/benchmark_results.csv`. Each benchmark execution appends new rows to this file, making it easy to track results over time.

### Columns in Results File

The results file contains the following columns:

| Column | Description |
|--------|-------------|
| `run_id` | UUID for the entire benchmark session |
| `timestamp` | ISO 8601 timestamp when query was submitted |
| `platform` | "snowflake" (for comparison with databricks) |
| `scenario` | "primary" (sequential execution) |
| `warehouse_name` | Full warehouse name (e.g., BENCHMARK_WH_MEDIUM) |
| `warehouse_size` | Size: SMALL, MEDIUM, or XLARGE |
| `query_num` | Query number (1-22) |
| `run_num` | Iteration number (1-4) |
| `run_type` | "cold" (first run) or "warm" (subsequent runs) |
| `query_tag` | Full tag like "tpch_sf100_primary_q01_run1" |
| `query_id` | Snowflake query ID for ACCOUNT_USAGE lookup |
| `execution_time_sec` | Total elapsed time (client-side measurement) |
| `rows_produced` | Number of rows returned (from enrichment) |
| `error_message` | Any error that occurred (empty if successful) |

### Enriching Results with ACCOUNT_USAGE Data

After waiting **45+ minutes** for `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` to populate, enrich the results with detailed metrics from Snowflake's internal monitoring:

```bash
uv run snowflake/enrich_results.py snowflake/results/benchmark_results.csv
```

**Note:** The enrichment script uses `BENCHMARK_WH_MEDIUM` to query the ACCOUNT_USAGE views. Ensure the BENCHMARK role has the necessary privileges on the SNOWFLAKE database (granted via IMPORTED PRIVILEGES).

This command updates the results file **in-place** by adding the following columns from ACCOUNT_USAGE for any rows that haven't been enriched yet:

- `compilation_time_ms` - Query compilation time
- `queued_time_ms` - Time spent queued
- `bytes_scanned` - Bytes scanned during execution
- `credits_used_cloud_services` - Cloud services credits consumed
- `credits_used_compute` - Compute credits consumed
- `total_elapsed_time_ms` - Total elapsed time (from Snowflake)

The enrichment script is idempotent - it only enriches rows that don't already have enrichment data, so you can safely run it multiple times. This is useful if you run additional benchmarks and want to enrich the new results.

## Query Tagging

All queries are tagged using the pattern: `tpch_sf100_primary_q{##}_run{#}`

Examples:
- `tpch_sf100_primary_q01_run1` - Query 1, first (cold) run
- `tpch_sf100_primary_q22_run4` - Query 22, fourth (warm) run

This allows easy filtering in Snowflake's query history:

```sql
SELECT *
FROM snowflake.account_usage.query_history
WHERE query_tag LIKE 'tpch_sf100%'
ORDER BY start_time;
```

## Cold vs Warm Runs

The benchmark implements the following pattern:

1. **Cold Run (run 1)**: First execution after warehouse cool-down
   - Warehouse starts from suspended state
   - No cache available
   - After execution, waits 180 seconds (3 minutes) for warehouse to suspend

2. **Warm Runs (runs 2-4)**: Subsequent executions
   - Warehouse already running
   - May benefit from cache (result cache is disabled, but metadata cache is active)
   - No delay between runs

## Cost Tracking

To track costs, query warehouse metering history after the benchmark:

```sql
SELECT
    warehouse_name,
    DATE_TRUNC('hour', start_time) as hour,
    SUM(credits_used) as total_credits
FROM snowflake.account_usage.warehouse_metering_history
WHERE warehouse_name IN (
    'BENCHMARK_WH_SMALL',
    'BENCHMARK_WH_MEDIUM',
    'BENCHMARK_WH_XLARGE'
)
AND start_time >= '2025-11-11'  -- Replace with your benchmark date
GROUP BY 1, 2
ORDER BY 1, 2;
```

## Troubleshooting

### Connection Issues

If you get authentication errors, verify your Snowflake CLI connection:

```bash
snow connection test --connection demo
```

Ensure `~/.snowflake/connections.toml` has valid credentials.

### Warehouse Permissions

If you get permission errors, ensure the BENCHMARK role has access:

```sql
USE ROLE ACCOUNTADMIN;
GRANT ALL ON WAREHOUSE BENCHMARK_WH_MEDIUM TO ROLE BENCHMARK;
```

### Query Failures

Check the `error_message` column in the results CSV for details. Common issues:
- Syntax errors (check adapted queries in `queries/` directory)
- Timeout (increase warehouse size or adjust query)
- Permission errors (grant access to SNOWFLAKE_SAMPLE_DATA)

### Enrichment Returns No Data

Wait at least 45 minutes after benchmark completion before running enrichment. ACCOUNT_USAGE has a latency of up to 45 minutes.

## Query Validation

To validate a single query before benchmarking:

```bash
# Test query 1
snow sql --connection demo -f snowflake/queries/q01.sql

# Test with timing
snow sql --connection demo -f snowflake/queries/q01.sql --format JSON
```

## Next Steps

After completing the Snowflake benchmark:

1. **Wait 45 minutes** and run enrichment
2. **Analyze results** using pandas or SQL
3. **Run Databricks benchmark** (in `../databricks/`)
4. **Compare platforms** using analysis scripts (in `../analysis/`)

## Notes

- Result caching is disabled (`USE_CACHED_RESULT = FALSE`) to ensure fair benchmarking
- The TPC-H SF100 dataset contains ~100GB of data across 8 tables
- All queries use fully qualified table names: `SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.*`
- Queries are adapted from the official TPC-H specification with standard substitution values
