# Snowflake Benchmark Analysis Tools

This directory contains DuckDB-based analysis tools for Snowflake benchmark results.

## Quick Start

### Interactive Dashboard (Recommended)

```bash
# From project root:
uv run streamlit run snowflake/analysis/dashboard.py

# Or from this directory (snowflake/analysis/):
uv run streamlit run dashboard.py
```

### Command-Line Analysis

```bash
# From this directory (snowflake/analysis/):
uv run analyze_results.py

# Or from project root:
cd snowflake/analysis
uv run analyze_results.py
```

## Files

- **[dashboard.py](dashboard.py)** - Interactive Streamlit dashboard with visualizations
- **[analyze_results.py](analyze_results.py)** - Main analysis script with comprehensive metrics
- **[analyze_example.py](analyze_example.py)** - Example showing how to use the analyzer as a library
- **[example_queries.sql](example_queries.sql)** - 10 advanced SQL query examples for custom analysis
- **[ANALYSIS.md](ANALYSIS.md)** - Full documentation
- **[QUICKSTART_ANALYSIS.md](QUICKSTART_ANALYSIS.md)** - Quick reference guide with key insights

## Common Commands

### Dashboard

```bash
# Launch interactive dashboard (opens in browser)
# Works from project root or analysis directory
uv run streamlit run snowflake/analysis/dashboard.py
```

### Command-Line Analysis

```bash
# Default analysis (summary + key metrics)
uv run analyze_results.py

# Full comprehensive analysis
uv run analyze_results.py --all

# Analyze a specific query
uv run analyze_results.py --query 9

# Export summary to CSV
uv run analyze_results.py --export summary.csv

# Run custom SQL
uv run analyze_results.py --sql "SELECT warehouse_size, AVG(execution_time_sec) FROM benchmark_results GROUP BY warehouse_size"

# Example analysis workflow
uv run analyze_example.py
```

## What Gets Analyzed

### Dashboard (Interactive)
The Streamlit dashboard provides 4 key visualizations:
1. **Warehouse Performance Comparison** - Bar charts showing mean/median execution times
2. **Query Performance Heatmap** - Color-coded matrix of query × warehouse performance
3. **Query Rankings** - Side-by-side charts of fastest and slowest queries
4. **Cold vs Warm Analysis** - Comparing first-run vs cached performance with speedup metrics

Includes interactive filters for warehouse size and run type.

### Command-Line Analysis
- **Performance by warehouse size** (SMALL, MEDIUM, XLARGE)
- **Run type comparison** (cold, semi-warm, warm)
- **Query performance rankings** (fastest/slowest queries)
- **Cold-to-warm speedup** (caching benefits)
- **Performance matrix** (query × warehouse size)
- **Custom metrics** via SQL queries

## Data Source

By default, analyzes: `../results/benchmark_results.csv`

## Documentation

See [ANALYSIS.md](ANALYSIS.md) for complete documentation and [QUICKSTART_ANALYSIS.md](QUICKSTART_ANALYSIS.md) for quick tips.
