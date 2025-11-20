# Snowflake vs Databricks Performance Benchmark

A Python-based benchmarking tool to compare query performance and cost between Snowflake and Databricks using the TPC-H SF1000 (1TB) dataset.

## What It Does

This benchmark executes all 22 TPC-H queries against both Snowflake and Databricks, measuring execution time, cost (credits/DBUs), and detailed performance metrics. Results are stored in DuckDB for analysis and comparison using dbt-generated views.

### Benchmark Modes

The tool supports three benchmarking scenarios:

1. **Normal (Sequential)**
   - Executes all 22 queries sequentially on a warm warehouse
   - Warehouse remains running throughout the entire run
   - First query experiences cold start, subsequent queries benefit from warm warehouse
   - Default mode for comprehensive performance testing

2. **Coldstart**
   - Warehouse suspended/stopped between each query
   - Each query experiences full cold start overhead (warehouse startup time)
   - Tests worst-case performance when no cache is available
   - Defaults to queries 1, 3, 5, 10, 18 (configurable)
   - Useful for understanding cold cache performance

3. **Concurrent**
   - All 22 queries executed in parallel on the same warehouse
   - Tests warehouse concurrency and resource contention
   - Measures performance degradation under concurrent load
   - Uses multi-cluster warehouses to handle parallel execution
   - Defaults to all 22 queries (configurable)

Use `--scenario normal`, `--scenario coldstart`, `--scenario concurrent`, or `--scenario all` (default) to run all three scenarios with a unified run ID.

## Getting Started

### 1. Install Dependencies

If you do not have `uv` installed, run `curl -LsSf https://astral.sh/uv/install.sh | sh`. See [uv docs](https://docs.astral.sh/uv/) for details and troubleshooting.

```bash
uv sync
```

> Note: `uv` will automatically install the Snowflake and Databricks CLI tools for you.

### 2. Configure Environment Variables (Automated)

Run the automated setup script from the **project root**:

```bash
uv run setup_config.py
```

This interactive script will:

- ✓ Prompt for your Snowflake connection name
- ✓ Prompt for Databricks workspace credentials
- ✓ Discover available catalogs and schemas
- ✓ Generate your `.env` file automatically

**Note:** SQL Warehouses are created and destroyed automatically during benchmark runs. No manual warehouse configuration needed.

**Warehouse Naming:** Warehouses are named with the pattern `{PREFIX}_{SIZE}_{SCENARIO}_{RUN_ID}` to prevent conflicts when running multiple scenarios. For example: `BENCHMARK_WH_MEDIUM_NORMAL_001` and `BENCHMARK_WH_MEDIUM_COLDSTART_001`.


---

### 2b. Configure Environment Variables (Manual)

If you prefer to manually configure, copy `.env.example` to `.env` and configure all user-specific environment variables for your environment.

#### Snowflake Configuration

Ensure you have the [Snowflake CLI installed and configured](https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation).

First, add your Snowflake CLI connection:

```bash
snow connection add --connection <your-connection-name>
snow connection test --connection <your-connection-name>
```

Then configure these variables in `.env`:

- **`SNOWFLAKE_CONNECTION`** - Your Snowflake CLI connection name (required)
- **`SNOWFLAKE_ROLE`** - Role to use for benchmark (default: `BENCHMARK`)
- **`SNOWFLAKE_DATABASE`** - Database for benchmark tables (default: `BENCHMARK`)
- **`SNOWFLAKE_SCHEMA`** - Schema for benchmark tables (default: `PUBLIC`)
- **`SNOWFLAKE_WAREHOUSE_PREFIX`** - Prefix for warehouse names (default: `BENCHMARK_WH`)
  - Full warehouse names will be: `{PREFIX}_small`, `{PREFIX}_medium`, `{PREFIX}_xlarge` with run IDs appended

Example:

```bash
export SNOWFLAKE_CONNECTION=my_connection
export SNOWFLAKE_ROLE=BENCHMARK
export SNOWFLAKE_DATABASE=MY_BENCHMARK_DB
export SNOWFLAKE_SCHEMA=PUBLIC
export SNOWFLAKE_WAREHOUSE_PREFIX=MY_WH
```

#### Databricks Configuration

Configure these variables in `.env`:

- **`DATABRICKS_HOST`** - Your Databricks workspace URL (required)
  - Format: `https://dbc-xxxxxxxxx.cloud.databricks.com`
- **`DATABRICKS_TOKEN`** - Your Databricks personal access token (required)
- **`DATABRICKS_CATALOG`** - Catalog for benchmark tables (required, user-specific)
- **`DATABRICKS_SCHEMA`** - Schema for benchmark tables (required, user-specific)

**Note:** SQL Warehouses are created and destroyed automatically during benchmark runs. No pre-configuration of warehouses needed.

Example:

```bash
export DATABRICKS_HOST=https://dbc-abc123.cloud.databricks.com
export DATABRICKS_TOKEN=dapi_abc123xyz789
export DATABRICKS_CATALOG=my_benchmark_catalog
export DATABRICKS_SCHEMA=my_benchmark_schema
```

### 3. Run Benchmarks

#### Basic Usage

```bash
# Run all scenarios (normal + coldstart + concurrent) with default settings (medium warehouse)
uv run main.py
```

#### Command-Line Options

| Flag | Options | Description |
|------|---------|-------------|
| `--warehouse-size` | `small`, `medium`, `large` | Warehouse size to use. Automatically maps to platform-specific sizes:<br>• `small`: Snowflake Small / Databricks X-Small<br>• `medium`: Snowflake Medium / Databricks Small (default)<br>• `large`: Snowflake X-Large / Databricks Large |
| `--scenario` | `normal`, `coldstart`, `concurrent`, `all` | Benchmark scenario to run:<br>• `normal`: Sequential queries with warm warehouse only<br>• `coldstart`: Warehouse suspended between each query only (defaults to queries 1,3,5,10,18 if not specified)<br>• `concurrent`: All queries executed in parallel on same warehouse<br>• `all`: Run all three scenarios with unified run ID (default) |
| `--queries` | e.g., `1,2,3` or `1-5` | Specific queries to run (default: all 22 TPC-H queries) |
| `--snowflake-only` | (flag) | Run only Snowflake benchmark (skip Databricks) |
| `--databricks-only` | (flag) | Run only Databricks benchmark (skip Snowflake) |

#### Examples

```bash
# Run all scenarios (normal + coldstart + concurrent) with default medium warehouse
uv run main.py

# Run with large warehouse (runs all three scenarios by default)
uv run main.py --warehouse-size large

# Run specific queries (all scenarios)
uv run main.py --queries 1,2,3
uv run main.py --queries 1-5

# Run ONLY normal scenario (warm warehouse)
uv run main.py --scenario normal

# Run ONLY cold start scenario (warehouse suspended between queries)
uv run main.py --scenario coldstart

# Run ONLY concurrent scenario (all queries in parallel)
uv run main.py --scenario concurrent

# Explicitly run all scenarios (same as default)
uv run main.py --scenario all

# Run cold start with specific queries
uv run main.py --scenario coldstart --queries 1,5,10

# Run concurrent with specific queries
uv run main.py --scenario concurrent --queries 1-10

# Run only Databricks
uv run main.py --databricks-only

# Run only Snowflake
uv run main.py --snowflake-only

# Combine flags: large warehouse, specific queries, all scenarios
uv run main.py --warehouse-size large --queries 1-10 --scenario all
```

### 4. Enrich Results with Cost and Performance Data

Both Snowflake and Databricks collect detailed cost and performance metrics in system tables, but this data is not immediately available. After running benchmarks, enrich all unenriched queries in the DuckDB database.

Run **at least 1-2 hours** after benchmark completion:

```bash
uv run enrich.py
```

This unified enrichment script runs the following in order:
1. **Snowflake query enrichment** - Data from `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY`
2. **Snowflake warehouse usage** - Data from `SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY`
3. **Databricks warehouse usage** - Data from `system.billing.usage`

**Snowflake enrichment adds:**
- Query compilation time
- Queue time (provisioning + repair + overload)
- Bytes scanned
- Cloud services credits used
- Total elapsed time (server-side)

**Databricks enrichment adds:**
- Warehouse usage data for DBU cost approximation
- Approximate DBU cost per query (proportionally distributed from warehouse-hour costs)

**Important Notes:**
- **Timing:** Snowflake data available after 45 minutes, Databricks may take 1-2 hours
- **Databricks costs:** DBU costs are **approximations** (proportionally distributed from warehouse-hour costs)
- **Snowflake costs:** Exact per-query credit tracking
- **Permissions required:**
  - Snowflake: `SELECT` on `SNOWFLAKE.ACCOUNT_USAGE.*`
  - Databricks: `SELECT` on `system.query.history` and `system.billing.usage`

### 5. View Results

After running benchmarks, view comparison reports using the dbt-generated views.

**Database Schema:**
- Database file: `benchmark_results.duckdb` (in project root)
- Schema: `benchmark_results.main`
- Raw tables: `snowflake_results`, `databricks_results`
- Analysis views: Generated by dbt (see below)

#### Build Analysis Views

```bash
# Build/refresh all analysis views
cd common/transformations
uvx dbt build
```

#### Query Results

**Command-line:**

```bash
# Query results for normal scenario (warm warehouse)
duckdb benchmark_results.duckdb -c "SELECT * FROM platform_comparison_normal;"

# Query results for coldstart scenario (suspended warehouse)
duckdb benchmark_results.duckdb -c "SELECT * FROM platform_comparison_coldstart;"

# Query results for concurrent scenario (parallel execution)
duckdb benchmark_results.duckdb -c "SELECT * FROM platform_comparison_concurrent;"

# Query latest run (all scenarios)
duckdb benchmark_results.duckdb -c "SELECT * FROM platform_comparison_latest;"
```

**GUI Tool (Recommended):**

Use [DBeaver](https://dbeaver.io/) for interactive querying and visualization:
1. Download and install DBeaver
2. Create a new DuckDB connection
3. Point to `benchmark_results.duckdb` in the project root
4. Query the views with full SQL editor and export capabilities

**Available Views:**
- `platform_comparison_normal` - Latest normal scenario (sequential queries, warm warehouse)
- `platform_comparison_coldstart` - Latest coldstart scenario (warehouse suspended between queries)
- `platform_comparison_concurrent` - Latest concurrent scenario (all queries in parallel)
- `platform_comparison_latest` - Latest run with all scenarios combined

See [common/transformations/README.md](common/transformations/README.md) for detailed documentation on the analysis views.

## Requirements

- Python 3.x with `uv` package manager
- Snowflake account with access to `SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000`
- Databricks workspace with TPC-H SF1000 dataset in Delta Lake

## Project Structure

- [`main.py`](main.py) - Main benchmark execution script
- [`snowflake/`](snowflake/) - Snowflake benchmark implementation
- [`databricks/`](databricks/) - Databricks benchmark implementation
- [`common/`](common/) - Shared utilities and transformations
  - [`transformations/`](common/transformations/) - dbt models for analysis views
- [`tests/`](tests/) - Test suite for benchmark logic
- [`project_plan.md`](project_plan.md) - Detailed implementation plan
- [`CLAUDE.md`](CLAUDE.md) - Development guidelines

## Testing

Run the test suite to verify benchmark logic and ensure code quality:

```bash
# Run all tests with test runner script
./run_tests.sh

# Or run manually with pytest
uv run pytest tests/ -v
```

The test suite includes 34 tests covering:
- Warehouse manager lifecycle (create, destroy, suspend/resume)
- Query executor logic and metrics collection
- Scenario integration (normal, coldstart, all)
- Run type classification (cold, semi-warm, warm)

Tests use mocks and do not require database connections.

