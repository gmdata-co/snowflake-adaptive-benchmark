# Snowflake TPC-H Benchmark

This module implements the Snowflake side of the TPC-H performance comparison, mirroring the Databricks benchmark structure with platform-specific adaptations.

## Architecture

The Snowflake benchmark uses a modular architecture:

- **`warehouse_manager.py`** - SQL Warehouse lifecycle management (create, destroy, suspend/resume)
- **`query_executor.py`** - Query execution and metrics collection
- **`benchmark.py`** - Orchestration using the managers
- **`enrich_results.py`** - Post-execution enrichment from ACCOUNT_USAGE

### Dynamic Warehouse Creation

Warehouses are created dynamically during benchmark runs for perfect cost attribution:

- **Warehouse naming**: `BENCHMARK_WH_{SIZE}_{SCENARIO}_{RUN_ID}`
  - Example: `BENCHMARK_WH_MEDIUM_NORMAL_001`, `BENCHMARK_WH_MEDIUM_COLDSTART_001`
- **Creation role**: SYSADMIN (grants to BENCHMARK role for execution)
- **Lifecycle**: Created at benchmark start, destroyed at end (via try/finally blocks)
- **Scenario isolation**: Separate warehouses for `normal` and `coldstart` scenarios prevent conflicts

### Query Execution

- Queries executed using `snowflake-connector-python`
- Query tags set via `session.query_tag` as JSON: `{"app": "tpchbenchmark", "workload_id": "q01", "run_id": "001"}`
- Query ID captured for correlation with ACCOUNT_USAGE tables
- Results written to `snowflake_results` table in DuckDB (`benchmark_results.duckdb`)

### Cost Tracking

Snowflake provides exact per-query cost tracking:

- **Query-level granularity**: Each query's credits tracked individually
- **Sources**: `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` provides exact credit usage
- **Enrichment**: Post-execution enrichment adds compilation time, queue time, bytes scanned, credits
- **Warehouse attribution**: Ephemeral warehouses enable perfect cost isolation per run

## Usage

**Important:** The Snowflake benchmark is executed via the main benchmark script (`main.py`), not directly. See the [main README](../README.md) for usage instructions.

### Quick Example

```bash
# Run both Snowflake and Databricks with medium warehouse
uv run main.py --warehouse-size medium

# Run only Snowflake
uv run main.py --snowflake-only --warehouse-size large

# Run coldstart scenario only
uv run main.py --snowflake-only --scenario coldstart
```

### Warehouse Size Mapping

The `--warehouse-size` flag maps to Snowflake-specific sizes:

| Generic Size | Snowflake Size |
|--------------|----------------|
| `small` | Small |
| `medium` | Medium (default) |
| `large` | X-Large |

### Warehouse Settings

All warehouses are created with:
- **Auto-suspend**: 120 seconds (2 minutes)
- **Auto-resume**: TRUE
- **Initially**: SUSPENDED
- **Result cache**: Disabled (`USE_CACHED_RESULT = FALSE`)

## Configuration

Set these environment variables in `.env`:

```bash
# Required
SNOWFLAKE_CONNECTION=my_connection  # From ~/.snowflake/connections.toml

# Optional (with defaults)
SNOWFLAKE_ROLE=BENCHMARK
SNOWFLAKE_DATABASE=BENCHMARK
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE_PREFIX=BENCHMARK_WH
```

Run `uv run setup_config.py` for interactive setup.

### Prerequisites

1. **Snowflake CLI** installed and configured:
   ```bash
   snow connection add --connection <your-connection-name>
   snow connection test --connection <your-connection-name>
   ```

2. **Benchmark resources** created (role, database):
   ```bash
   source .env
   snow sql --connection $SNOWFLAKE_CONNECTION -f snowflake/project_setup.sql
   ```

   This creates:
   - Role: `BENCHMARK`
   - Database: `BENCHMARK`
   - Grants: Access to `SNOWFLAKE_SAMPLE_DATA` and `SNOWFLAKE` (for ACCOUNT_USAGE)

3. **TPC-H data**: Access to `SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000` (1TB dataset)

## Run Types

Queries are classified by warehouse state:

- **cold**: First query on warehouse (or after warehouse suspended/resumed in coldstart scenario)
- **semi-warm**: New query on warm warehouse
- **warm**: Repeated query on warm warehouse

## Results

Results are stored in DuckDB at `benchmark_results.duckdb`:

```sql
-- View Snowflake results from latest run
SELECT * FROM snowflake_results
WHERE run_id = (SELECT MAX(run_id) FROM snowflake_results)
ORDER BY query_num, run_num;

-- Use dbt-generated comparison views (recommended)
SELECT * FROM platform_comparison_normal;      -- Normal scenario
SELECT * FROM platform_comparison_coldstart;   -- Coldstart scenario
SELECT * FROM platform_comparison_latest;      -- Latest run (all scenarios)
```

See [common/transformations/README.md](../common/transformations/README.md) for details on analysis views.

### Result Schema

The `snowflake_results` table contains:

| Column | Description |
|--------|-------------|
| `run_id` | Unique run identifier (e.g., "001") |
| `timestamp` | ISO 8601 timestamp when query was submitted |
| `platform` | "snowflake" |
| `scenario` | "normal" or "coldstart" |
| `warehouse_name` | Full warehouse name (e.g., BENCHMARK_WH_MEDIUM_NORMAL_001) |
| `warehouse_size` | SMALL, MEDIUM, or XLARGE |
| `query_num` | Query number (1-22) |
| `run_num` | Iteration number within run |
| `run_type` | cold, semi-warm, or warm |
| `query_tag` | JSON query tag for filtering |
| `query_id` | Snowflake query ID for ACCOUNT_USAGE lookup |
| `execution_time_sec` | Total elapsed time (client-side) |
| `error_message` | Any error that occurred (NULL if successful) |

**Enrichment columns** (added by `enrich_results.py`):
- `compilation_time_ms` - Query compilation time
- `queued_time_ms` - Time spent queued (provisioning + repair + overload)
- `bytes_scanned` - Bytes scanned during execution
- `cloud_services_credits` - Cloud services credits consumed
- `total_elapsed_time_ms` - Total elapsed time (server-side from Snowflake)

## Enrichment

After running benchmarks, enrich results with detailed metrics from system tables.

**Recommended:** Use the unified enrichment script from the project root:

```bash
# Wait at least 1-2 hours after benchmark completion
uv run enrich.py
```

This runs both Snowflake and Databricks enrichment in the correct order.

**Snowflake-only enrichment** (if needed):

```bash
# Wait at least 45 minutes after benchmark completion
uv run snowflake/enrich_results.py
```

This enriches all unenriched queries in DuckDB with data from `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY`:

- Query compilation time
- Queue time (provisioning + repair + overload)
- Bytes scanned
- Cloud services credits used
- Total elapsed time (server-side)

**Latency:** Snowflake's ACCOUNT_USAGE has a documented 45-minute latency. Wait at least 45 minutes before enriching.

**Permissions Required:**
- `SELECT` on `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` (granted via `project_setup.sql`)

## Scenario Support

### Normal Scenario
- Sequential query execution on warm warehouse
- All 22 TPC-H queries (default)
- Warehouse remains running throughout
- First query classified as `cold`, subsequent as `semi-warm` or `warm`

### Coldstart Scenario
- Warehouse suspended/resumed between each query
- Default queries: 1, 3, 5, 10, 18 (override with `--queries`)
- Each query experiences full cold start (~15-30 sec warehouse resume)
- All queries classified as `cold`

## Query Tagging

All queries are tagged with JSON for filtering and analysis:

```json
{
  "app": "tpchbenchmark",
  "workload_id": "q01",
  "run_id": "001"
}
```

Use tags to filter in ACCOUNT_USAGE:

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
```

## Cost Tracking

### By Run ID

Track costs for a specific benchmark run:

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

Verify your Snowflake CLI connection:

```bash
source .env
snow connection test --connection $SNOWFLAKE_CONNECTION
```

Ensure `~/.snowflake/connections.toml` has valid credentials.

### Warehouse Creation Failures

If warehouse creation fails:

1. **Check SYSADMIN access**: Connection must have SYSADMIN privileges
2. **Check quotas**: Ensure account has available warehouse quota
3. **Check permissions**: Verify BENCHMARK role exists (`project_setup.sql`)

Common error:
```
SQL access control error: Insufficient privileges to operate on warehouse
```
**Solution:** Use connection with SYSADMIN or ACCOUNTADMIN role.

### Query Failures

Check `error_message` column in DuckDB results. Common issues:
- Syntax errors (check queries in `queries/adapted_queries/`)
- Timeout (increase warehouse size)
- Permission errors (ensure access to `SNOWFLAKE_SAMPLE_DATA`)

### Enrichment Returns No Data

Wait at least 45 minutes after benchmark completion. ACCOUNT_USAGE has documented 45-minute latency.

### Orphaned Warehouses

If benchmark crashes and warehouses aren't destroyed:

```sql
-- List all benchmark warehouses
SHOW WAREHOUSES LIKE 'BENCHMARK_WH_%';

-- Drop specific warehouse
DROP WAREHOUSE BENCHMARK_WH_MEDIUM_NORMAL_001;

-- Drop all benchmark warehouses (CAREFUL - verify list first!)
-- First: SHOW WAREHOUSES LIKE 'BENCHMARK_WH_%';
```

## Query Validation

To validate a single query before benchmarking:

```bash
source .env

# Test query 1
snow sql --connection $SNOWFLAKE_CONNECTION -f snowflake/queries/adapted_queries/q01.sql

# Test with timing
snow sql --connection $SNOWFLAKE_CONNECTION -f snowflake/queries/adapted_queries/q01.sql --format JSON
```

## Key Differences from Databricks

| Aspect | Snowflake | Databricks |
|--------|-----------|------------|
| **Warehouse Creation** | Dynamic via SQL | Dynamic via SDK (WorkspaceClient) |
| **Cost Granularity** | Exact per-query credits | Approximated from warehouse-hour DBUs |
| **System Table Latency** | 45 min (documented) | Hours (undocumented, variable) |
| **Cold Start** | Suspend/resume warehouse | Stop/start warehouse |
| **Connection** | snowflake-connector-python | databricks-sql-connector |
| **Query Tags** | session.query_tag (JSON) | SQL comment /* BENCHMARK: {...} */ |

## Module Files

- **`warehouse_manager.py`** - Manages warehouse lifecycle
- **`query_executor.py`** - Executes queries and collects metrics
- **`benchmark.py`** - Main orchestration logic
- **`enrich_results.py`** - Enriches results from ACCOUNT_USAGE
- **`queries/adapted_queries/`** - TPC-H SF1000 query SQL files (q01.sql - q22.sql)
- **`project_setup.sql`** - One-time Snowflake resource setup

## Notes

- Result caching is disabled (`USE_CACHED_RESULT = FALSE`) to ensure fair benchmarking
- TPC-H datasets available at multiple scale factors (SF1000 = 1TB, SF10000 = 10TB)
- All queries use fully qualified names: `SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000.*`
- Queries adapted from official TPC-H specification with standard substitution values
- Warehouses are ephemeral - created per run and destroyed automatically
- Sequential run IDs enable perfect cost attribution per benchmark execution
