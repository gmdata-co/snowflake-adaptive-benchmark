# Benchmark Results Analysis with DuckDB

This document describes how to use the DuckDB-based analysis tool to analyze benchmark results.

## Overview

The [`analyze_results.py`](analyze_results.py) script provides comprehensive analysis of benchmark results using DuckDB queries. It can analyze performance across warehouse sizes, run types (cold/warm/semi-warm), and individual queries.

## Installation

DuckDB is already included in the project dependencies. If you need to add it manually:

```bash
uv add duckdb
```

## Usage

### Basic Analysis (Default)

Shows summary statistics, warehouse comparison, run type comparison, and top 5 fastest/slowest queries:

```bash
uv run python analyze_results.py
```

### Full Analysis

Run all available analyses:

```bash
uv run python analyze_results.py --all
```

This includes:
- Summary statistics
- Performance by warehouse size
- Performance by run type (cold/warm/semi-warm)
- Top 10 fastest and slowest queries
- Query performance matrix
- Cold to warm speedup analysis

### Detailed Query Analysis

Analyze a specific query number (e.g., query 9):

```bash
uv run python analyze_results.py --query 9
```

### Export Summary to CSV

Export aggregated summary statistics to a CSV file:

```bash
uv run python analyze_results.py --export output_summary.csv
```

The exported CSV includes:
- Warehouse size
- Query number
- Run type
- Run count
- Average, median, min, max execution times
- Standard deviation

### Custom SQL Queries

Execute custom SQL queries against the benchmark data:

```bash
uv run python analyze_results.py --sql "SELECT warehouse_size, AVG(execution_time_sec) FROM benchmark_results GROUP BY warehouse_size"
```

### Specify Results File

By default, the script looks for results at `../results/benchmark_results.csv` (relative to this analysis directory). To use a different file:

```bash
uv run python analyze_results.py --results path/to/results.csv
```

## Available Analyses

### 1. Summary Statistics
- Total runs
- Unique run IDs
- Unique queries
- Warehouse sizes
- Min/max/average/median execution times

### 2. Warehouse Comparison
Performance metrics grouped by warehouse size (SMALL, MEDIUM, XLARGE):
- Total runs
- Average execution time
- Median execution time
- Min/max execution times
- Standard deviation

### 3. Run Type Comparison
Performance comparison across run types:
- **Cold**: First run with warehouse starting from idle
- **Semi-warm**: First run of a new query on an active warehouse
- **Warm**: Subsequent runs with cached data/compiled queries

### 4. Query Performance Ranking
- Top 10 fastest queries by average execution time
- Top 10 slowest queries by average execution time

### 5. Query Performance Matrix
A table showing average execution time for each query across all warehouse sizes, making it easy to spot:
- Which queries benefit most from larger warehouses
- Which queries have consistent performance across sizes
- Performance outliers

### 6. Cold to Warm Speedup
Analysis showing:
- Average cold run time
- Average warm run time
- Time saved
- Speedup percentage by warehouse size

## Example Output

### Summary Statistics
```
================================================================================
SUMMARY STATISTICS
================================================================================

 total_runs  unique_run_ids  unique_queries  warehouse_sizes  min_exec_time  max_exec_time  avg_exec_time  median_exec_time
        264               1              22                3          0.997          19.28       5.731799            4.2365
```

### Warehouse Comparison
```
================================================================================
PERFORMANCE BY WAREHOUSE SIZE
================================================================================

warehouse_size  total_runs  avg_exec_time  median_exec_time  min_exec_time  max_exec_time  stddev_exec_time
         SMALL          88          7.403             6.135          1.020         19.280             4.820
        MEDIUM          88          5.561             4.527          0.997         18.991             3.963
        XLARGE          88          4.232             3.325          1.050         17.322             3.637
```

## Data Schema

The analysis expects a CSV with the following columns:
- `run_id`: Unique identifier for the benchmark run
- `timestamp`: When the query was executed
- `platform`: Platform name (e.g., "snowflake")
- `scenario`: Test scenario (e.g., "primary")
- `warehouse_name`: Name of the warehouse
- `warehouse_size`: Size of warehouse (SMALL, MEDIUM, XLARGE, etc.)
- `query_num`: Query number (1-22 for TPC-H)
- `run_num`: Run number within the query (1 = first run, 2+ = subsequent)
- `run_type`: Type of run (cold, semi-warm, warm)
- `query_tag`: JSON tag with metadata
- `query_id`: Unique query execution ID
- `execution_time_sec`: Query execution time in seconds
- `rows_produced`: Number of rows produced
- `error_message`: Any error message (if applicable)
- Additional metadata columns

## Tips

### Finding Performance Issues

1. **Identify slow queries**:
   ```bash
   uv run python analyze_results.py --sql "SELECT query_num, AVG(execution_time_sec) as avg_time FROM benchmark_results GROUP BY query_num HAVING avg_time > 10 ORDER BY avg_time DESC"
   ```

2. **Check variance across runs**:
   ```bash
   uv run python analyze_results.py --sql "SELECT query_num, STDDEV(execution_time_sec) as stddev FROM benchmark_results WHERE run_type='warm' GROUP BY query_num ORDER BY stddev DESC LIMIT 10"
   ```

3. **Compare warehouse efficiency**:
   ```bash
   uv run python analyze_results.py --sql "SELECT warehouse_size, query_num, AVG(execution_time_sec) FROM benchmark_results WHERE run_type='warm' GROUP BY warehouse_size, query_num ORDER BY query_num, warehouse_size"
   ```

### Performance Analysis Workflow

1. Run the full analysis to get an overview:
   ```bash
   uv run python analyze_results.py --all
   ```

2. Identify interesting queries (very fast, very slow, or high variance)

3. Deep dive into specific queries:
   ```bash
   uv run python analyze_results.py --query <query_num>
   ```

4. Export summary for further analysis in spreadsheets:
   ```bash
   uv run python analyze_results.py --export summary.csv
   ```

## Extending the Analysis

The `BenchmarkAnalyzer` class can be imported and extended in your own scripts:

```python
from analyze_results import BenchmarkAnalyzer

# Create analyzer
analyzer = BenchmarkAnalyzer("path/to/results.csv")

# Run built-in analyses
analyzer.summary_stats()
analyzer.warehouse_comparison()

# Execute custom queries
analyzer.custom_query("SELECT * FROM benchmark_results WHERE query_num = 1")

# Close connection
analyzer.close()
```

## Troubleshooting

### CSV Loading Issues

The script uses pandas to load CSV files (more forgiving than DuckDB's CSV reader for complex fields). If you encounter issues:

1. Ensure the CSV has a header row
2. Check for unusual characters in JSON fields
3. Verify the file encoding is UTF-8

### Missing Data

If certain analyses show empty results:
- Check that your data has the expected `run_type` values (cold, warm, semi-warm)
- Verify warehouse size values match expected format (SMALL, MEDIUM, XLARGE)
- Ensure `execution_time_sec` is numeric

## Related Files

- [`benchmark.py`](../benchmark.py) - Runs the benchmarks and generates results
- [`benchmark_results.csv`](../results/benchmark_results.csv) - Raw benchmark results
- [`project_plan.md`](../../project_plan.md) - Overall project plan and methodology
