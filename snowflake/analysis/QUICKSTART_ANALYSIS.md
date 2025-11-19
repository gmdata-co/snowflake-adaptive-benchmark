# Quick Start: Analyzing Benchmark Results

## TL;DR - Common Commands

```bash
# Default summary (fastest way to get insights)
uv run analyze_results.py

# Full comprehensive analysis
uv run analyze_results.py --all

# Deep dive into a specific query
uv run analyze_results.py --query 9

# Export summary for spreadsheet analysis
uv run analyze_results.py --export summary.csv

# Custom SQL query
uv run analyze_results.py --sql "SELECT warehouse_size, AVG(execution_time_sec) FROM benchmark_results WHERE query_num < 10 GROUP BY warehouse_size"
```

## Key Insights from Current Data

Based on your benchmark results (264 runs across 22 queries):

### Warehouse Performance
- **XLARGE**: 4.23s avg (fastest, 43% faster than SMALL)
- **MEDIUM**: 5.56s avg (good balance)
- **SMALL**: 7.40s avg (slowest but most cost-effective)

### Run Type Performance
- **Cold runs**: 5.74s avg (warehouse starting from idle)
- **Semi-warm runs**: 6.53s avg (new query on active warehouse)
- **Warm runs**: 5.48s avg (cached/compiled queries)

### Query Performance
**Fastest queries** (great candidates for real-time dashboards):
- Query 6: 1.17s avg
- Query 14: 1.43s avg
- Query 15: 1.53s avg

**Slowest queries** (optimization candidates):
- Query 9: 14.85s avg
- Query 2: 9.90s avg
- Query 11: 9.85s avg
- Query 21: 9.68s avg
- Query 10: 9.49s avg

## Next Steps

1. **Investigate slow queries**: Focus on queries 9, 2, 11, 21, 10
   ```bash
   uv run analyze_results.py --query 9
   ```

2. **Check cold-to-warm speedup**: See how much caching helps
   ```bash
   uv run analyze_results.py --all | grep -A 10 "COLD TO WARM"
   ```

3. **Export for deeper analysis**: Use Excel/Google Sheets for charts
   ```bash
   uv run analyze_results.py --export analysis.csv
   ```

4. **Compare specific warehouse sizes**: Custom SQL for targeted analysis
   ```bash
   uv run analyze_results.py --sql "
     SELECT
       query_num,
       AVG(CASE WHEN warehouse_size='MEDIUM' THEN execution_time_sec END) as medium,
       AVG(CASE WHEN warehouse_size='XLARGE' THEN execution_time_sec END) as xlarge,
       AVG(CASE WHEN warehouse_size='MEDIUM' THEN execution_time_sec END) -
       AVG(CASE WHEN warehouse_size='XLARGE' THEN execution_time_sec END) as time_saved
     FROM benchmark_results
     WHERE run_type='warm'
     GROUP BY query_num
     ORDER BY time_saved DESC
     LIMIT 10
   "
   ```

## Understanding the Data

### Run Types Explained
- **cold**: First run after warehouse idle (includes startup time)
- **semi-warm**: First run of a new query on already-running warehouse
- **warm**: Subsequent runs (benefits from result caching & query compilation)

### Key Metrics
- **avg_exec_time**: Mean execution time (affected by outliers)
- **median_exec_time**: Middle value (better for skewed distributions)
- **stddev_exec_time**: Consistency indicator (low = predictable performance)

## Tips

- Run `--all` after each benchmark to spot trends
- Use `--query X` to investigate performance anomalies
- Export regularly to track performance over time
- Use custom SQL to answer specific questions

For detailed documentation, see [ANALYSIS.md](ANALYSIS.md)
