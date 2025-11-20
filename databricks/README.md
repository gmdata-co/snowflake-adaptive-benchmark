# Databricks TPC-H Benchmark

This module implements the Databricks side of the TPC-H performance comparison, mirroring the Snowflake benchmark structure with platform-specific adaptations.

## Architecture

The Databricks benchmark uses a modular architecture:

- **`warehouse_manager.py`** - SQL Warehouse lifecycle management (create, destroy, stop/start)
- **`query_executor.py`** - Query execution and metrics collection
- **`benchmark.py`** - Orchestration using the managers
- **`enrich_results.py`** - Post-execution enrichment from system tables

### Dynamic Warehouse Creation

Like Snowflake, Databricks warehouses are created dynamically during benchmark runs:

- **Warehouse naming**: `BENCHMARK_WH_{SIZE}_{SCENARIO}_{RUN_ID}`
  - Example: `BENCHMARK_WH_SMALL_NORMAL_001`, `BENCHMARK_WH_SMALL_COLDSTART_001`
- **Warehouse type**: Serverless SQL Warehouses (created via `databricks.sdk.WorkspaceClient`)
- **Lifecycle**: Created at benchmark start, destroyed at end (via try/finally blocks)
- **Scenario isolation**: Separate warehouses for `normal` and `coldstart` scenarios prevent conflicts

### Query Execution

- Queries executed using `databricks-sql-connector`
- Query tags added as SQL comments: `/* BENCHMARK: {...} */`
- Statement ID captured from cursor for correlation with system tables
- Results written to `databricks_results` table in DuckDB (`benchmark_results.duckdb`)

### Cost Tracking

Unlike Snowflake's exact per-query credit tracking, Databricks cost attribution works differently:

- **Warehouse-level billing**: DBUs charged per warehouse-hour
- **Query-level approximation**: Costs distributed proportionally across queries based on execution time
- **Enrichment source**: `system.billing.usage` table provides warehouse usage data
- **Calculation**: Total warehouse DBUs × (query execution time / total warehouse runtime)

**Note:** This is an approximation. Databricks does not provide exact per-query DBU costs like Snowflake provides per-query credits.

## Usage

**Important:** The Databricks benchmark is executed via the main benchmark script (`main.py`), not directly. See the [main README](../README.md) for usage instructions.

### Quick Example

```bash
# Run both Snowflake and Databricks with medium warehouse
uv run main.py --warehouse-size medium

# Run only Databricks
uv run main.py --databricks-only --warehouse-size large

# Run coldstart scenario only
uv run main.py --databricks-only --scenario coldstart
```

### Warehouse Size Mapping

The `--warehouse-size` flag maps to Databricks-specific sizes:

| Generic Size | Databricks Size | Cluster Config |
|--------------|-----------------|----------------|
| `small` | X-Small | Serverless, 2X-Small |
| `medium` | Small | Serverless, Small (default) |
| `large` | Large | Serverless, Large |

## Configuration

Set these environment variables in `.env`:

```bash
# Required
DATABRICKS_HOST=https://dbc-abc123.cloud.databricks.com
DATABRICKS_TOKEN=dapi_abc123xyz789
DATABRICKS_CATALOG=my_benchmark_catalog
DATABRICKS_SCHEMA=my_benchmark_schema
```

Run `uv run setup_config.py` for interactive setup that discovers available catalogs and schemas.

## Run Types

Queries are classified by warehouse state:

- **cold**: First query on warehouse (or after warehouse stopped/started in coldstart scenario)
- **semi-warm**: New query on warm warehouse
- **warm**: Repeated query on warm warehouse

## Results

Results are stored in DuckDB at `benchmark_results.duckdb`:

```sql
-- View Databricks results from latest run
SELECT * FROM databricks_results
WHERE run_id = (SELECT MAX(run_id) FROM databricks_results)
ORDER BY query_num, run_num;

-- Use dbt-generated comparison views (recommended)
SELECT * FROM platform_comparison_normal;      -- Normal scenario
SELECT * FROM platform_comparison_coldstart;   -- Coldstart scenario
SELECT * FROM platform_comparison_latest;      -- Latest run (all scenarios)
```

See [common/transformations/README.md](../common/transformations/README.md) for details on analysis views.

## Enrichment

After running benchmarks, enrich results with detailed metrics from system tables.

**Use the unified enrichment script** from the project root:

```bash
# Wait at least 1-2 hours after benchmark completion
uv run enrich.py
```

This runs both Snowflake and Databricks enrichment in the correct order.

**Note:** The standalone `databricks/enrich_results.py` script has known issues and should not be run directly. Use the unified `enrich.py` script instead.

**What gets enriched:**
- Warehouse usage data from `system.billing.usage`
- Approximate DBU cost per query (proportionally distributed from warehouse-hour costs)

**Latency:** Databricks system table latency is **undocumented and variable**. Data may take hours to appear.

**Permissions Required:**
- `SELECT` on `system.query.history`
- `SELECT` on `system.billing.usage`

## Scenario Support

### Normal Scenario
- Sequential query execution on warm warehouse
- All 22 TPC-H queries (default)
- Warehouse remains running throughout
- First query classified as `cold`, subsequent as `semi-warm` or `warm`

### Coldstart Scenario
- Warehouse stopped between each query
- Default queries: 1, 3, 5, 10, 18 (override with `--queries`)
- Each query experiences full cold start (~30-60 sec warehouse startup)
- All queries classified as `cold`

## Troubleshooting

### DuckDB Lock Error
Close any applications with `benchmark_results.duckdb` open:
```bash
lsof benchmark_results.duckdb  # Check what's locking the file
```

### Connection Error
Ensure Databricks credentials are loaded:
```bash
source ~/.zshrc  # If credentials stored in zshrc
```

Verify `.env` has required variables:
```bash
grep DATABRICKS .env
```

### Warehouse Creation Failure
Check that your Databricks token has permissions to:
- Create SQL Warehouses (`CREATE SQL_WAREHOUSE`)
- Stop/start SQL Warehouses (`USE SQL_WAREHOUSE`)
- Query data in specified catalog/schema (`SELECT` on tables)

### Enrichment Missing Data
If enrichment finds no data:
1. Wait longer (system tables can be delayed by hours)
2. Verify `statement_id` was captured during query execution
3. Check permissions on `system.query.history` and `system.billing.usage`
4. Confirm warehouse usage appears in Databricks billing console

## Key Differences from Snowflake

| Aspect | Snowflake | Databricks |
|--------|-----------|------------|
| **Warehouse Creation** | Dynamic via SQL | Dynamic via SDK (WorkspaceClient) |
| **Cost Granularity** | Exact per-query credits | Approximated from warehouse-hour DBUs |
| **System Table Latency** | 45 min (documented) | Hours (undocumented, variable) |
| **Cold Start** | Suspend/resume warehouse | Stop/start warehouse |
| **Connection** | snowflake-connector-python | databricks-sql-connector |
| **Warehouse Naming** | Includes scenario | Includes scenario |

## Module Files

- **`warehouse_manager.py`** - Manages SQL Warehouse lifecycle
- **`query_executor.py`** - Executes queries and collects metrics
- **`benchmark.py`** - Main orchestration logic
- **`enrich_results.py`** - Enriches results from system tables
- **`queries/`** - TPC-H SF1000 query SQL files (q01.sql - q22.sql)
- **`SETUP.md`** - One-time Databricks workspace setup instructions
