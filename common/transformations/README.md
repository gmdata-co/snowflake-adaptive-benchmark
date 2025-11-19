# Benchmark Analysis Views (dbt)

This directory contains dbt models for creating analysis views from benchmark results.

## Overview

The transformation layer uses **dbt-duckdb** to create organized, tested views for analyzing Snowflake vs Databricks benchmark results. Views are automatically generated from the benchmark results database with proper dependency management.

## Quick Start

### Build All Views

```bash
# From the transformations directory
./build_views.sh

# Or manually
uv run dbt build --profiles-dir .
```

### Query the Views

```bash
# Normal scenario comparison
duckdb ../../benchmark_results.duckdb -c "SELECT * FROM platform_comparison_normal;"

# Coldstart scenario comparison
duckdb ../../benchmark_results.duckdb -c "SELECT * FROM platform_comparison_coldstart;"

# Latest run (all scenarios)
duckdb ../../benchmark_results.duckdb -c "SELECT * FROM platform_comparison_latest;"
```

## Views

### Mart Views (Primary Views)

1. **`platform_comparison_normal`** - Latest normal scenario run
   - Sequential queries with warm warehouse
   - Benefits from caching and warm compute
   - Use this to compare typical performance

2. **`platform_comparison_coldstart`** - Latest coldstart scenario run
   - Warehouse suspended between each query
   - Measures true cold start performance
   - Use this to compare worst-case performance

3. **`platform_comparison_latest`** - Latest run_id, all scenarios
   - Includes all scenarios from the most recent run
   - Grouped by scenario
   - Use this when you ran multiple scenarios together

### View Columns

All comparison views include:
- `query_num` - TPC-H query number (1-22, or 999999 for total)
- `snowflake_seconds` - Execution time on Snowflake
- `dbx_seconds` - Execution time on Databricks
- `snowflake_cost` - Proportionally allocated cost
- `dbx_cost` - Proportionally allocated cost
- `row_count` - Number of rows produced
- `status` - Execution status (success, error, etc.)
- `scenario` - Benchmark scenario (in platform_comparison_latest only)

## Project Structure

```
transformations/
├── dbt_project.yml          # dbt project configuration
├── profiles.yml             # DuckDB connection config
├── build_views.sh           # Convenience script to build views
├── models/
│   ├── base/                # Source table references
│   │   ├── base_snowflake_results.sql
│   │   ├── base_databricks_results.sql
│   │   └── sources.yml
│   ├── intermediate/        # Filtered and aggregated data
│   │   ├── int_snowflake_latest_by_scenario.sql
│   │   ├── int_databricks_latest_by_scenario.sql
│   │   ├── int_snowflake_costs.sql
│   │   └── int_databricks_costs.sql
│   └── marts/               # Final comparison views
│       ├── platform_comparison_normal.sql
│       ├── platform_comparison_coldstart.sql
│       ├── platform_comparison_latest.sql
│       └── schema.yml       # Tests and documentation
└── README.md                # This file
```

## Running Tests

```bash
# Run all data quality tests
uv run dbt test --profiles-dir .
```

Tests verify:
- No null values in critical columns
- Valid scenario values (normal, coldstart, concurrent, TOTAL)
- Valid status values (success, error variants, TOTAL)

## How It Works

### Dependency Graph

```
Sources (benchmark results tables)
  ↓
Base Models (passthrough with docs)
  ↓
Intermediate Models (latest by scenario + costs)
  ↓
Mart Models (final comparison views)
```

dbt automatically builds models in the correct order based on `ref()` dependencies.

### Scenario Handling

The views filter results by scenario:
- **normal** - Sequential execution, warm warehouse
- **coldstart** - Warehouse suspended between queries
- **concurrent** - Parallel execution (future)

Each scenario gets its own latest run:
- `int_snowflake_latest_by_scenario` finds the latest run for each scenario
- Comparison views filter to specific scenarios or include all

### Cost Allocation

Warehouse costs are allocated proportionally to queries based on execution time:
```
query_cost = (query_time / total_time) * total_warehouse_cost
```

## Adding New Views

1. Create a new SQL file in `models/marts/`
2. Use `{{ ref('model_name') }}` to reference other models
3. Add documentation to `models/marts/schema.yml`
4. Run `uv run dbt build --profiles-dir .`

## Migration from Old System

The old numbered SQL files (01_*.sql, 02_*.sql, etc.) have been replaced with this dbt setup.

**Benefits of dbt:**
- Automatic dependency management (no more numbered files!)
- Built-in testing framework
- Better organization as views grow
- Self-documenting with schema.yml

## Troubleshooting

### Database locked
If you see "database is locked", close any DuckDB connections:
```bash
# Make sure no other processes are using the database
lsof | grep benchmark_results.duckdb
```

### Views are empty
Make sure you've run benchmarks first:
```bash
# Run a quick benchmark to populate data
python main.py --scenario normal --queries 1,2 --warehouse-size medium
```

### Tests failing
Run with verbose output to see details:
```bash
uv run dbt test --profiles-dir . --debug
```
