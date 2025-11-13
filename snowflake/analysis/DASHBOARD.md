# Streamlit Dashboard Guide

Interactive visualization dashboard for Snowflake benchmark results.

## Launch

```bash
# From project root:
uv run streamlit run snowflake/analysis/dashboard.py

# Or from snowflake/analysis directory:
cd snowflake/analysis
uv run streamlit run dashboard.py
```

The dashboard will automatically open in your default web browser at `http://localhost:8501`.

**Note:** The dashboard automatically finds the benchmark data file regardless of which directory you run it from.

## Features

### Overview Metrics (Top)
Five key metrics displayed at the top:
- **Total Runs** - Total number of query executions
- **Unique Queries** - Number of distinct queries tested
- **Avg Exec Time** - Average execution time across all runs
- **Min/Max Time** - Fastest and slowest query times

### Sidebar Filters

#### Primary Filter
- **Benchmark Run** - Select a specific benchmark run by ID and timestamp, or view all runs combined
  - Shows run ID (first 8 chars) and timestamp for easy identification
  - Defaults to showing all runs
  - Applies to the entire dataset before other filters

#### Secondary Filters
- **Warehouse Size** - Filter by SMALL, MEDIUM, XLARGE, or view All
- **Run Type** - Filter by cold, warm, semi-warm, or view All

### Visualizations

#### 1. Performance by Warehouse Size
- **Bar chart** comparing mean vs median execution times across warehouse sizes
- **Data table** with detailed statistics (mean, median, std dev, min, max)
- Shows how larger warehouses generally reduce execution time

#### 2. Query Performance Heatmap
- **Color-coded matrix** showing average execution time for each query on each warehouse size
- **Red** = slow queries, **Green** = fast queries
- Helps identify:
  - Which queries benefit from larger warehouses
  - Which queries are consistently fast/slow
  - Outlier performance patterns

#### 3. Query Performance Rankings
Two side-by-side charts:
- **Top 10 Fastest Queries** (green bars) - Candidates for real-time dashboards
- **Top 10 Slowest Queries** (red bars) - Optimization candidates

#### 4. Cold vs Warm Performance
- **Grouped bar chart** comparing cold start (red) vs warm cached runs (green)
- **Speedup table** showing:
  - Average cold/warm times by warehouse
  - Time saved from caching
  - Speedup percentage
- Demonstrates the value of query result caching and warehouse keep-alive

## Tips

### Analyzing Multiple Benchmark Runs
1. Use the **Benchmark Run** filter to compare different runs side-by-side
2. Switch between runs to see if performance improved after optimizations
3. Select "All Runs" to see aggregate performance across all benchmarks
4. Run timestamps help identify which benchmarks are most recent

### Finding Performance Issues
1. Use the **heatmap** to spot queries that don't scale well (same color across warehouse sizes)
2. Check the **slowest queries** chart for optimization candidates
3. Use **filters** to focus on specific warehouse sizes or run types

### Cost Optimization
1. Compare **warehouse performance** to see if XLARGE is worth the cost
2. Look at **cold vs warm** speedup to determine optimal warehouse auto-suspend settings
3. Identify **fast queries** that can run on smaller (cheaper) warehouses

### Interactive Exploration
- **Hover** over charts for detailed values
- Use **sidebar filters** to drill down into specific scenarios
- Charts are automatically updated when filters change

## Screenshots

The dashboard includes:
- Clean, professional layout with Snowflake branding
- Responsive design that works on different screen sizes
- Color-coded visualizations for quick insights
- Interactive Plotly charts with zoom, pan, and hover details

## Data Refresh

The dashboard automatically loads data from `../results/benchmark_results.csv`. To see updated results:
1. Run new benchmarks
2. Refresh your browser (or use Streamlit's "Rerun" button)

## Troubleshooting

### Dashboard won't start
- Ensure you're in the `snowflake/analysis` directory
- Check that `../results/benchmark_results.csv` exists
- Verify streamlit is installed: `uv add streamlit plotly`

### Charts not showing
- Verify the CSV file has data
- Check browser console for errors
- Try clearing browser cache

### Filters not working
- Ensure you have data for the selected filter combinations
- Some queries may only have certain run types (e.g., only warm runs)

## Advanced Usage

### Custom Port
```bash
uv run streamlit run dashboard.py --server.port 8502
```

### Headless Mode
```bash
uv run streamlit run dashboard.py --server.headless true
```

### Different Data File
Edit `dashboard.py` and change the `default` parameter in the `load_data()` function.

## Next Steps

- See [ANALYSIS.md](ANALYSIS.md) for detailed metrics explanations
- Use [analyze_results.py](analyze_results.py) for scriptable analysis
- Check [example_queries.sql](example_queries.sql) for custom SQL queries
