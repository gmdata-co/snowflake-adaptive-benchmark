# Snowflake TPC-H Benchmark

This directory contains the Snowflake benchmarking setup for TPC-H datasets for comparison against Databricks.

## Overview

The benchmark executes all 22 TPC-H queries against Snowflake warehouses and logs detailed performance metrics for analysis and comparison. Warehouses are created dynamically for each benchmark run and destroyed afterward for perfect cost attribution.

## Prerequisites

1. **Snowflake Account** with access to `SNOWFLAKE_SAMPLE_DATA.TPCH_SF*` datasets
2. **Snowflake CLI** configured with a connection (name specified in `.env` file's `SNOWFLAKE_CONNECTION` variable)
3. **Python 3.11+** with `uv` package manager
4. **Benchmark Setup** completed (role and database created)
5. **Environment configured** (copy `.env.example` to `.env` and update with your connection details)

## Project Structure

```
snowflake/
├── README.md                 # This file
├── config.py                 # Configuration constants
├── benchmark.py              # Main benchmark execution script
├── enrich_results.py         # Post-run enrichment from ACCOUNT_USAGE
├── clear_results.py          # Safely clear benchmark results
├── adapt_queries.py          # Query adaptation script (already run)
├── project_setup.sql         # Snowflake role/database setup
├── queries/                  # TPC-H queries (q01.sql - q22.sql)
│   ├── adapted_queries/
│   │   ├── q01.sql - q22.sql
│   │   ├── QUERY_CATEGORIES.md
│   │   └── README.md
│   └── original_queries/
└── results/                  # Benchmark results
    ├── benchmark_results.csv # Single CSV with all benchmark runs
    └── backups/              # Automatic backups when clearing data
```

## Setup

### 1. Create Snowflake Resources

Run the project setup to create the necessary role and database:

```bash
source .env  # Load connection name from environment
snow sql --connection $SNOWFLAKE_CONNECTION -f snowflake/project_setup.sql
```

This creates:
- **Role**: `BENCHMARK`
- **Database**: `BENCHMARK`
- **Grants**: Access to `SNOWFLAKE_SAMPLE_DATA` and `SNOWFLAKE` database

**Note:** Warehouses are **NOT** created manually. They are created automatically by the benchmark script with unique run IDs and destroyed afterward.

### 2. Install Dependencies

Dependencies are already installed via uv if you've set up the project:

```bash
# From project root
uv sync
```

## Running the Benchmark

### Basic Usage

Run the complete benchmark (all 22 queries, 1 run each, medium warehouse only):

```bash
uv run snowflake/benchmark.py
```

This will:
1. Generate a sequential run ID (001, 002, 003, etc.)
2. Create medium warehouse with run ID suffix (e.g., `BENCHMARK_WH_MEDIUM_001`)
3. Execute all queries on the medium warehouse
4. Destroy warehouse at the end
5. Save results to DuckDB

**Default:** Medium warehouse only. To test multiple sizes, use `--warehouse` flag multiple times.

### Customize Benchmark Run

#### Test Multiple Warehouse Sizes

```bash
# Test all three warehouse sizes
uv run snowflake/benchmark.py --warehouse small --warehouse medium --warehouse xlarge

# Test small and medium only
uv run snowflake/benchmark.py --warehouse small --warehouse medium
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
# Run 4 iterations per query to test cold vs warm performance
uv run snowflake/benchmark.py --runs 4
```

#### Change Scale Factor

```bash
# Use SF10000 (10TB dataset)
uv run snowflake/benchmark.py --scale-factor 10000
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
    Default: medium only

--queries "1,3,5,..."
    Comma-separated list of query numbers to run
    Default: all 22 queries (1-22)

--runs N
    Number of runs per query
    Default: 1 (single run per query)

--scale-factor N
    TPC-H scale factor (1000 = 1TB, 10000 = 10TB)
    Default: 1000

--connection NAME
    Snowflake connection name from ~/.snowflake/connections.toml
    Default: value from SNOWFLAKE_CONNECTION environment variable (.env file)

--sequential
    Run warehouses sequentially instead of in parallel
    Default: parallel execution
```

## Dynamic Warehouse Management

### How It Works

The benchmark script implements **ephemeral warehouse creation** for perfect cost attribution:

1. **Run ID Generation**: Sequential run IDs (001, 002, 003...) are generated from existing CSV data
2. **Warehouse Creation**: Warehouses are created with run ID suffix (e.g., `BENCHMARK_WH_MEDIUM_001`)
3. **Parallel Execution**: All warehouses for a run share the same run ID suffix
4. **Automatic Cleanup**: Warehouses are destroyed automatically at the end (even if errors occur)

### Benefits

- **Perfect Cost Attribution**: Each run's costs are isolated to specific warehouses
- **No Manual Cleanup**: Warehouses are destroyed automatically via try/finally
- **Easy Cost Tracking**: Filter `warehouse_metering_history` by warehouse name pattern
- **Multiple Concurrent Runs**: Different runs use different warehouses (001, 002, etc.)

### Warehouse Naming Convention

Format: `BENCHMARK_WH_{SIZE}_{RUN_ID}`

Examples:
- `BENCHMARK_WH_SMALL_001` - Small warehouse for run 001
- `BENCHMARK_WH_MEDIUM_001` - Medium warehouse for run 001
- `BENCHMARK_WH_XLARGE_001` - X-Large warehouse for run 001
- `BENCHMARK_WH_MEDIUM_002` - Medium warehouse for run 002

### Warehouse Settings

All warehouses are created with:
- **Auto-suspend**: 120 seconds (2 minutes)
- **Auto-resume**: TRUE
- **Initially suspended**: TRUE

## Understanding the Results

### Benchmark Results File

All benchmark runs are logged to a single CSV file at `snowflake/results/benchmark_results.csv`. Each benchmark execution appends new rows to this file, making it easy to track results over time.

### Columns in Results File

The results file contains the following columns:

| Column | Description |
|--------|-------------|
| `run_id` | Sequential run ID (001, 002, 003...) |
| `timestamp` | ISO 8601 timestamp when query was submitted |
| `platform` | "snowflake" (for comparison with databricks) |
| `scenario` | "primary" (sequential execution) |
| `warehouse_name` | Full warehouse name (e.g., BENCHMARK_WH_MEDIUM_001) |
| `warehouse_size` | Size: SMALL, MEDIUM, or XLARGE |
| `query_num` | Query number (1-22) |
| `run_num` | Iteration number (1-4) |
| `run_type` | "cold" (first run) or "warm" (subsequent runs) |
| `query_tag` | JSON structured tag for filtering |
| `query_id` | Snowflake query ID for ACCOUNT_USAGE lookup |
| `execution_time_sec` | Total elapsed time (client-side measurement) |
| `rows_produced` | Number of rows returned (from enrichment) |
| `error_message` | Any error that occurred (empty if successful) |

### Enriching Results with ACCOUNT_USAGE Data

After waiting **45+ minutes** for `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` to populate, enrich the results with detailed metrics from Snowflake's internal monitoring:

```bash
uv run snowflake/enrich_results.py snowflake/results/benchmark_results.csv
```

This command updates the results file **in-place** by adding the following columns from ACCOUNT_USAGE for any rows that haven't been enriched yet:

- `compilation_time_ms` - Query compilation time
- `queued_time_ms` - Time spent queued
- `bytes_scanned` - Bytes scanned during execution
- `credits_used_cloud_services` - Cloud services credits consumed
- `credits_used_compute` - Compute credits consumed
- `total_elapsed_time_ms` - Total elapsed time (from Snowflake)

The enrichment script is idempotent - it only enriches rows that don't already have enrichment data, so you can safely run it multiple times. This is useful if you run additional benchmarks and want to enrich the new results.

## Managing Results

### List All Runs

View a summary of all benchmark runs in the results file:

```bash
uv run snowflake/clear_results.py --list
```

This displays:
- Run ID and timestamp range
- Platform and warehouses used
- Number of queries and total executions
- Enrichment status

### Clear Results Data

The `clear_results.py` script provides safe ways to clear benchmark data:

**Clear all data (with automatic backup):**
```bash
uv run snowflake/clear_results.py --clear-all
```

**Clear specific run by run_id:**
```bash
uv run snowflake/clear_results.py --clear-run 001
```

**Clear without creating backup (not recommended):**
```bash
uv run snowflake/clear_results.py --clear-all --no-backup
```

**Important Notes:**
- By default, a timestamped backup is created in `results/backups/` before clearing
- You must type "yes" to confirm deletion
- The script shows exactly what will be deleted before confirming
- Backups are named with timestamps: `benchmark_results_YYYYMMDD_HHMMSS.csv`

## Query Tagging

All queries are tagged using a JSON structure for better filtering and analysis:

```json
{
  "app": "tpchbenchmark",
  "workload_id": "q01",
  "run_id": "001"
}
```

Fields:

- `app`: Application name ("tpchbenchmark")
- `workload_id`: Query identifier (e.g., "q01" for Query 1)
- `run_id`: Sequential run ID for the benchmark session

This allows flexible filtering in Snowflake's query history:

```sql
-- Find all queries from a specific benchmark run
SELECT *
FROM snowflake.account_usage.query_history
WHERE query_tag:run_id = '001'
ORDER BY start_time;

-- Find all executions of a specific query
SELECT *
FROM snowflake.account_usage.query_history
WHERE query_tag:app = 'tpchbenchmark'
  AND query_tag:workload_id = 'q01'
ORDER BY start_time;

-- Find all benchmark queries
SELECT *
FROM snowflake.account_usage.query_history
WHERE query_tag:app = 'tpchbenchmark'
ORDER BY start_time;
```

## Cold vs Warm Runs

By default, the benchmark runs each query once (NUM_RUNS = 1). To test cold vs warm performance, use `--runs 4`:

1. **Cold Run (run 1)**: First execution after warehouse creation
   - Warehouse starts from suspended state
   - No cache available
   - Classified as "cold" run type

2. **Warm Runs (runs 2-4)**: Subsequent executions (when using --runs 4)
   - Warehouse already running
   - May benefit from cache (result cache is disabled, but metadata cache is active)
   - Classified as "warm" or "semi-warm" depending on query repetition
   - No delay between runs

## Cost Tracking

### By Run ID

Track costs for a specific benchmark run by filtering warehouse metering history:

```sql
SELECT
    warehouse_name,
    DATE_TRUNC('hour', start_time) as hour,
    SUM(credits_used) as total_credits
FROM snowflake.account_usage.warehouse_metering_history
WHERE warehouse_name LIKE 'BENCHMARK_WH_%_001'  -- Replace 001 with your run_id
AND start_time >= '2025-11-13'  -- Replace with your benchmark date
GROUP BY 1, 2
ORDER BY 1, 2;
```

### By Scale Factor

```sql
-- Track costs across multiple runs for a specific scale factor
SELECT
    warehouse_name,
    SUM(credits_used) as total_credits
FROM snowflake.account_usage.warehouse_metering_history
WHERE warehouse_name LIKE 'BENCHMARK_WH_%'
AND start_time >= '2025-11-13'
GROUP BY 1
ORDER BY 1;
```

### Total Benchmark Costs

```sql
SELECT
    SUM(credits_used) as total_credits,
    SUM(credits_used_compute) as compute_credits,
    SUM(credits_used_cloud_services) as cloud_services_credits
FROM snowflake.account_usage.warehouse_metering_history
WHERE warehouse_name LIKE 'BENCHMARK_WH_%'
AND start_time >= '2025-11-13';
```

## Troubleshooting

### Connection Issues

If you get authentication errors, verify your Snowflake CLI connection:

```bash
source .env  # Load connection name from environment
snow connection test --connection $SNOWFLAKE_CONNECTION
```

Ensure `~/.snowflake/connections.toml` has valid credentials.

### Warehouse Creation Failures

If warehouse creation fails:

1. **Check SYSADMIN access**: The connection must have SYSADMIN privileges to create warehouses
2. **Check quotas**: Ensure your account has available warehouse quota
3. **Check permissions**: Verify the BENCHMARK role exists and has necessary grants

Common errors:
```
SQL access control error: Insufficient privileges to operate on warehouse
```
Solution: Grant CREATE WAREHOUSE to SYSADMIN or use a connection with ACCOUNTADMIN role.

### Query Failures

Check the `error_message` column in the results CSV for details. Common issues:
- Syntax errors (check adapted queries in `queries/` directory)
- Timeout (increase warehouse size or adjust query)
- Permission errors (grant access to SNOWFLAKE_SAMPLE_DATA)

### Enrichment Returns No Data

Wait at least 45 minutes after benchmark completion before running enrichment. ACCOUNT_USAGE has a latency of up to 45 minutes.

### Orphaned Warehouses

If the benchmark crashes and warehouses aren't destroyed:

```sql
-- List all benchmark warehouses
SHOW WAREHOUSES LIKE 'BENCHMARK_WH_%';

-- Drop specific warehouse
DROP WAREHOUSE BENCHMARK_WH_MEDIUM_001;

-- Or drop all benchmark warehouses (BE CAREFUL!)
-- Run SHOW WAREHOUSES first to verify the list!
```

## Query Validation

To validate a single query before benchmarking:

```bash
source .env  # Load connection name from environment

# Test query 1
snow sql --connection $SNOWFLAKE_CONNECTION -f snowflake/queries/adapted_queries/q01.sql

# Test with timing
snow sql --connection $SNOWFLAKE_CONNECTION -f snowflake/queries/adapted_queries/q01.sql --format JSON
```

## Next Steps

After completing the Snowflake benchmark:

1. **Wait 45 minutes** and run enrichment
2. **Analyze results** using pandas or SQL
3. **Run Databricks benchmark** (in `../databricks/`)
4. **Compare platforms** using analysis scripts (in `../analysis/`)

## Notes

- Result caching is disabled (`USE_CACHED_RESULT = FALSE`) to ensure fair benchmarking
- TPC-H datasets are available at multiple scale factors:
  - SF1000: ~1TB data (default)
  - SF10000: ~10TB data
- All queries use fully qualified table names: `SNOWFLAKE_SAMPLE_DATA.TPCH_SF{scale_factor}.*`
- Queries are adapted from the official TPC-H specification with standard substitution values
- Warehouses are ephemeral - created per run and destroyed automatically
- Sequential run IDs enable perfect cost attribution per benchmark execution
