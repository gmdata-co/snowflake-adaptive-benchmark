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
- ✓ Automatically discover your SQL warehouses
- ✓ Let you select which warehouses to use (X-Small, Small, Large)
- ✓ Discover available catalogs and schemas
- ✓ Generate your `.env` file automatically

**That's it!** No manual copying of warehouse IDs needed.

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

Ensure you have [Databricks CLI configured](https://docs.databricks.com/en/dev-tools/cli/install.html).

Configure these variables in `.env`:

- **`DATABRICKS_HOST`** - Your Databricks workspace URL (required)
  - Format: `https://dbc-xxxxxxxxx.cloud.databricks.com`
- **`DATABRICKS_TOKEN`** - Your Databricks personal access token (required)
- **`DATABRICKS_CATALOG`** - Catalog for benchmark tables (required, user-specific)
- **`DATABRICKS_SCHEMA`** - Schema for benchmark tables (required, user-specific)
- **`DATABRICKS_WAREHOUSE_XSMALL`** - SQL Warehouse ID for X-Small size (required)
- **`DATABRICKS_WAREHOUSE_SMALL`** - SQL Warehouse ID for Small size (required)
- **`DATABRICKS_WAREHOUSE_LARGE`** - SQL Warehouse ID for Large size (required)

To find warehouse IDs: Go to your Databricks workspace → SQL Warehouses → click each warehouse and copy the ID from the URL or settings.

Example:

```bash
export DATABRICKS_HOST=https://dbc-abc123.cloud.databricks.com
export DATABRICKS_TOKEN=dapi_abc123xyz789
export DATABRICKS_CATALOG=my_benchmark_catalog
export DATABRICKS_SCHEMA=my_benchmark_schema
export DATABRICKS_WAREHOUSE_XSMALL=abc123def456
export DATABRICKS_WAREHOUSE_SMALL=def456ghi789
export DATABRICKS_WAREHOUSE_LARGE=ghi789jkl012
```

### 3. Run Benchmarks

```bash
# Run with default warehouse sizes (medium for Snowflake, small for Databricks)
uv run python main.py

# Or run benchmarks individually
uv run python snowflake/benchmark.py  # Runs medium warehouse only
uv run python databricks/benchmark.py  # Runs small warehouse only
```

**Note:** By default, benchmarks run with medium-sized warehouses only. To test multiple warehouse sizes, use the `--warehouse` flag (see platform-specific READMEs).

### 4. Enrich Results with Cost and Performance Data

Both Snowflake and Databricks collect detailed cost and performance metrics in system tables, but this data is not immediately available. After running benchmarks, you can enrich all unenriched queries in the DuckDB database.

#### Snowflake Enrichment

Run **at least 45 minutes** after benchmark completion:

```bash
uv run python snowflake/enrich_results.py
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
uv run python databricks/enrich_results.py
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

## What It Does

- Executes TPC-H queries on both platforms
- Tracks execution time, cost (credits/DBUs), and performance metrics
- Tags queries for cost attribution
- Compares cold vs warm query performance
- Enriches results with detailed billing and performance data from platform system tables

## Requirements

- Python 3.x with `uv` package manager
- Snowflake account with access to `SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000`
- Databricks workspace with TPC-H SF1000 dataset in Delta Lake

## Project Structure

- [`main.py`](main.py) - Main benchmark execution script
- [`project_plan.md`](project_plan.md) - Detailed implementation plan
- [`CLAUDE.md`](CLAUDE.md) - Development guidelines

