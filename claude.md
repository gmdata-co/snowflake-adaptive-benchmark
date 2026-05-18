# Snowflake Adaptive vs Gen1 Performance Benchmark

## Groundrules

- This project uses uv. Do not use the uv pip wrapper, only use uv native commands like uv add.
- always run python using `uv run <name-of-file>`. no need to activate a venv.
- use the logging module instead of `print()`
- use the logger created in common/logging_config.py
- Use the snowflake CLI `snow` to run test queries or to do any setup. For example, if you need to figure out if your suggested SQL is valid, just run it real quick using `snow sql -q ...`
- when using the snowflake cli, use the `--connection` flag with the value specified in the `.env` file's `SNOWFLAKE_CONNECTION` variable.
- the goal is to benchmark Snowflake Adaptive warehouses against classic Gen1 warehouses and publish the result as the article in `visualization/`.
- any time you need to connect to snowflake with python, use the global connection module in the common folder: `connections/snowflake_connection.py`.
- whenever I mention duckDB, I mean the file called `benchmark_results.duckdb` in the project root.
- in duckdb, the schema we use is always benchmark_results.main
- if duckdb is locked when you try to use it, just stop and ask me to close it. Don't start doing crazy work arounds.
- after you write a bunch of python code, run `uvx ruff check --fix` to make sure unused imports and other linting issues are cleaned up. Please inspect the output of this command to see if there were any unfixable violations, and help fix them.

## Implementation Details

### Architecture Patterns
- **Separation of Concerns**: Benchmark modules under `snowflake/` are split into:
  - `warehouse_manager.py` - Warehouse lifecycle (create, destroy, suspend/resume)
  - `query_executor.py` - Query execution and metrics collection
  - `benchmark.py` - Orchestration using the managers
- **3-track concurrency**: `scripts/run_3track.sh` runs three isolated tracks
  (adaptive / gen1-tail / gen1-notail) on uniquely-named warehouses, each
  writing its own DuckDB; `merge_tracks.py` merges them into the canonical
  `benchmark_results.duckdb`.
- **idle_policy** is a real run-time column (wait_for_suspend | immediate_drop |
  n_a) — no post-hoc run_id guessing.

### Analysis (dbt)
- Run `./common/transformations/build_views.sh` (or `uv run dbt build
  --profiles-dir .` inside `common/transformations`) to rebuild views.
- The active model chain is `base_snowflake_results` → `adaptive_vs_gen1_summary`,
  which feeds `visualization/update_data.py` → `benchmarkData.json`.
