# Databricks TPC-H Benchmark

This benchmark mirrors the Snowflake benchmark structure but is adapted for Databricks SQL Warehouses.

## Key Differences from Snowflake

### Architecture
- **No dynamic warehouse creation**: Uses pre-configured warehouses from `config.py`
- **Simpler connection model**: Each instance connects to one warehouse
- **Synchronous execution**: No async query polling needed
- **Optional stop/start**: Can stop/start warehouses for cold runs instead of creating/destroying

### Cost Optimization
Unlike Snowflake's approach of creating ephemeral warehouses, this benchmark:
- ✅ Reuses existing warehouses (configured in `config.py`)
- ✅ Optionally stops/starts warehouses for cold runs (~30 sec startup vs 2-5 min for new warehouse)
- ✅ Avoids expensive warehouse creation/destruction cycles
- ✅ Same auto-suspend settings as configured in Databricks UI

### Query Execution
- Query tags added as SQL comments: `/* BENCHMARK: {...} */`
- Statement ID captured from cursor (if available)
- Results written to `databricks_results` table in DuckDB

## Usage

### Basic Usage (Default: Small Warehouse Only)
```bash
uv run python databricks/benchmark.py
```

**Note:** By default, only the small warehouse is used. To test multiple sizes, use the `--warehouse` flag.

### Test with Single Query
```bash
uv run python databricks/benchmark.py --warehouse small --queries 1 --runs 1
```

### Sequential Execution
```bash
uv run python databricks/benchmark.py --sequential
```

### With Cold Starts (Stop/Start Warehouses)
```bash
uv run python databricks/benchmark.py --stop-start
```
**Note**: This will stop all warehouses before the benchmark and start them as needed. Adds ~30 sec per warehouse but ensures true cold cache behavior.

### Multiple Warehouse Sizes
```bash
# Test all three warehouse sizes
uv run python databricks/benchmark.py --warehouse xsmall --warehouse small --warehouse large

# Test xsmall and small only
uv run python databricks/benchmark.py --warehouse xsmall --warehouse small
```

### Specific Queries
```bash
uv run python databricks/benchmark.py --queries "1,3,5,7"
```

## Configuration

Edit `databricks/config.py` to configure:

```python
WAREHOUSES = {
    "xsmall": "f9de55834a86c9db",  # Warehouse ID
    "small": "81c01fce5f1c223c",   # Primary baseline
    "large": "e2ce84a538ff2ada",
}

NUM_RUNS = 1          # Runs per query (default)
NUM_QUERIES = 22      # All TPC-H queries
SCALE_FACTOR = 1000   # 1TB dataset
```

## Run Types

Same classification as Snowflake:
- **cold**: First query on a warehouse (or after stop/start)
- **semi-warm**: Warehouse running, but this specific query hasn't run yet
- **warm**: Re-running same query on running warehouse

## Results

Results are stored in DuckDB at `benchmark_results.duckdb` in the `databricks_results` table:

```sql
-- View all results
SELECT * FROM databricks_results;

-- View latest run
SELECT * FROM databricks_results
WHERE run_id = (SELECT MAX(run_id) FROM databricks_results)
ORDER BY query_num, run_num;

-- Compare with Snowflake
SELECT
    platform,
    warehouse_size,
    query_num,
    run_type,
    AVG(execution_time_sec) as avg_time_sec
FROM (
    SELECT * FROM snowflake_results
    UNION ALL
    SELECT * FROM databricks_results
)
GROUP BY platform, warehouse_size, query_num, run_type
ORDER BY query_num, warehouse_size, platform;
```

## Troubleshooting

### DuckDB Lock Error
If you see "Conflicting lock is held", close any applications with the DuckDB file open (like DBeaver):
```bash
# Check what's locking the file
lsof benchmark_results.duckdb
```

### Connection Error
Make sure Databricks credentials are loaded:
```bash
source ~/.zshrc
```

Check `.env` file has:
```
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-token-here
```

### Missing Query Files
Verify all 22 queries exist:
```bash
ls databricks/queries/q*.sql | wc -l  # Should be 22
```

## API Usage

The `--stop-start` flag uses Databricks REST API to stop/start warehouses:
- `POST /api/2.0/sql/warehouses/{id}/stop`
- `POST /api/2.0/sql/warehouses/{id}/start`
- `GET /api/2.0/sql/warehouses/{id}` (for status polling)

This provides true cold cache isolation without the cost of creating new warehouses.
