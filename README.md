# Snowflake vs Databricks Performance Benchmark

A Python-based benchmarking tool to compare query performance and cost between Snowflake and Databricks using TPC-H SF100 (100GB dataset).  

See [`project_plan.md`](project_plan.md) for complete testing methodology and cost estimates.

## Quick Start

```bash
# Install dependencies
uv sync

# Run benchmarks
python main.py # not yet implemented!!
```

## What It Does (or will do)

- Executes TPC-H queries on both platforms
- Tracks execution time, cost (credits/DBUs), and performance metrics
- Tags queries for cost attribution
- Compares cold vs warm query performance

## Requirements

- Python 3.x with `uv` package manager
- Snowflake account with access to `SNOWFLAKE_SAMPLE_DATA.TPCH_SF100`
- Databricks workspace with TPC-H SF100 dataset in Delta Lake
- Snowflake CLI (`snow`) configured with connection specified in `.env` file's `SNOWFLAKE_CONNECTION` variable
- Environment file configured (copy `.env.example` to `.env` and update with your credentials)

## Project Structure

- [`main.py`](main.py) - Main benchmark execution script
- [`project_plan.md`](project_plan.md) - Detailed implementation plan
- [`CLAUDE.md`](CLAUDE.md) - Development guidelines

