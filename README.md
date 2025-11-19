# Snowflake vs Databricks Performance Benchmark

A Python-based benchmarking tool to compare query performance and cost between Snowflake and Databricks using TPC-H SF1000 (1TB dataset).

## Getting Started

### 1. Install Dependencies

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
# Run all scenarios (normal + coldstart) with default settings (medium warehouse)
uv run main.py
```

#### Command-Line Options

| Flag | Options | Description |
|------|---------|-------------|
| `--warehouse-size` | `small`, `medium`, `large` | Warehouse size to use. Automatically maps to platform-specific sizes:<br>• `small`: Snowflake Small / Databricks X-Small<br>• `medium`: Snowflake Medium / Databricks Small (default)<br>• `large`: Snowflake X-Large / Databricks Large |
| `--scenario` | `normal`, `coldstart`, `all` | Benchmark scenario to run:<br>• `normal`: Sequential queries with warm warehouse only<br>• `coldstart`: Warehouse suspended between each query only<br>• `all`: Run both scenarios with unified run ID (default) |
| `--queries` | e.g., `1,2,3` or `1-5` | Specific queries to run (default: all 22 TPC-H queries) |
| `--snowflake-only` | (flag) | Run only Snowflake benchmark (skip Databricks) |
| `--databricks-only` | (flag) | Run only Databricks benchmark (skip Snowflake) |

#### Examples

```bash
# Run with large warehouse (runs both scenarios by default)
uv run main.py --warehouse-size large

# Run specific queries (both scenarios)
uv run main.py --queries 1,2,3
uv run main.py --queries 1-5

# Run ONLY normal scenario (warm warehouse)
uv run main.py --scenario normal

# Run ONLY cold start scenario (warehouse suspended between queries)
uv run main.py --scenario coldstart

# Explicitly run all scenarios (same as default)
uv run main.py --scenario all

# Run cold start with specific queries
uv run main.py --scenario coldstart --queries 1,5,10

# Run only Databricks
uv run main.py --databricks-only

# Run only Snowflake
uv run main.py --snowflake-only

# Combine flags: large warehouse, specific queries, all scenarios
uv run main.py --warehouse-size large --queries 1-10 --scenario all
```

### 4. Enrich Results with Cost and Performance Data

Both Snowflake and Databricks collect detailed cost and performance metrics in system tables, but this data is not immediately available. After running benchmarks, you can enrich all unenriched queries in the DuckDB database.

#### Snowflake Enrichment

Run **at least 45 minutes** after benchmark completion:

```bash
uv run snowflake/enrich_results.py
```

This enriches all unenriched queries in DuckDB with data from `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY`:

- ✓ Query compilation time
- ✓ Queue time (provisioning + repair + overload)
- ✓ Bytes scanned
- ✓ Cloud services credits used
- ✓ Total elapsed time (server-side)

**Note:** Snowflake's ACCOUNT_USAGE has a documented 45-minute latency.

#### Databricks Enrichment

Run **at least 1-2 hours** after benchmark completion:

```bash
uv run databricks/enrich_results.py
```

This enriches all unenriched queries in DuckDB with data from `system.query.history` and `system.billing.usage`:

- ✓ Query compilation time
- ✓ Bytes read/scanned
- ✓ Server-side execution time
- ✓ Approximate DBU cost per query (proportionally distributed from warehouse-hour costs)

**Important Notes:**

- Databricks system table latency is **undocumented and variable** (may take hours)
- DBU costs are **approximations** calculated by distributing warehouse-hour costs proportionally across queries based on execution time
- This differs from Snowflake's exact per-query credit tracking
- Requires SELECT permissions on `system.query.history` and `system.billing.usage`

### 5. View Results

After running benchmarks, view comparison reports using the dbt-generated views:

```bash
# Build/refresh all analysis views
cd common/transformations
./build_views.sh

# Query results for normal scenario (warm warehouse)
duckdb ../../benchmark_results.duckdb -c "SELECT * FROM platform_comparison_normal;"

# Query results for coldstart scenario (suspended warehouse)
duckdb ../../benchmark_results.duckdb -c "SELECT * FROM platform_comparison_coldstart;"

# Query latest run (all scenarios)
duckdb ../../benchmark_results.duckdb -c "SELECT * FROM platform_comparison_latest;"
```

**Available Views:**
- `platform_comparison_normal` - Latest normal scenario (sequential queries, warm warehouse)
- `platform_comparison_coldstart` - Latest coldstart scenario (warehouse suspended between queries)
- `platform_comparison_latest` - Latest run with all scenarios combined

See [common/transformations/README.md](common/transformations/README.md) for detailed documentation on the analysis views.

## What It Does

- Executes TPC-H queries on both platforms
- Tracks execution time, cost (credits/DBUs), and performance metrics
- Tags queries for cost attribution
- Compares cold vs warm query performance
- Enriches results with detailed billing and performance data from platform system tables
- Generates comparison views using dbt for easy analysis by scenario

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

