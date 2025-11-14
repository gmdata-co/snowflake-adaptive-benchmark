# Snowflake vs Databricks Performance Benchmark

A Python-based benchmarking tool to compare query performance and cost between Snowflake and Databricks using TPC-H SF100 (100GB dataset).

## Getting Started

### 1. Install Dependencies

```bash
uv sync
```

> Note: `uv` will automatically install the Snowflake and Databricks CLI tools for you.

### 2. Configure Snowflake

Ensure you have the [Snowflake CLI installed and configured](https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation). Test your connection:

# Add your Snowflake CLI connection first:
snow connection add --connection <your-connection-name>

# Then test the connection:
snow connection test --connection <your-connection-name>

Copy `.env.example` to `.env` and add your Snowflake connection name:

```bash
SNOWFLAKE_CONNECTION=<your-connection-name>
```

### 3. Configure Databricks

Ensure you have [Databricks CLI configured](https://docs.databricks.com/en/dev-tools/cli/install.html).

Add your Databricks workspace host and token to the `.env` file:

```bash
DATABRICKS_HOST=<your-workspace-url>
DATABRICKS_TOKEN=<your-token>
```

### 4. Run Benchmarks

```bash
uv run python main.py
```

## What It Does

- Executes TPC-H queries on both platforms
- Tracks execution time, cost (credits/DBUs), and performance metrics
- Tags queries for cost attribution
- Compares cold vs warm query performance

## Requirements

- Python 3.x with `uv` package manager
- Snowflake account with access to `SNOWFLAKE_SAMPLE_DATA.TPCH_SF100`
- Databricks workspace with TPC-H SF100 dataset in Delta Lake

## Project Structure

- [`main.py`](main.py) - Main benchmark execution script
- [`project_plan.md`](project_plan.md) - Detailed implementation plan
- [`CLAUDE.md`](CLAUDE.md) - Development guidelines

