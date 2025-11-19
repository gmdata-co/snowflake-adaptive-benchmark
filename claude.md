# Snwoflake vs Databricks Performance Comparison

## Groundrules

- This project uses uv. Do not use the uv pip wrapper, only use uv native commands like uv add.
- always run python using `uv run <name-of-file>`. no need to activate a venv.
- use the logging module instead of `print()`
- us the logger created in common/logging_config.py
- Use the snowflake CLI `snow` to run test queries or to do any setup. For example, if you need to figure out if your suggested SQL is valid, just run it real quick using `snow sql -q ...`
- when using the snowflake cli, use the `--connection` flag with the value specified in the `.env` file's `SNOWFLAKE_CONNECTION` variable.
- the goal is to create a python file that will run multiple queries against snowflake and databricks.
- the overall project plan is at `project_plan.md`.
- dbx is short for databricks.
- run `source ~/.zshrc` to get the databricks credentials loaded.
- any time you need to connect to snowflake or dbx with python, use the global connections modules in the common folder: connections/databricks_connection.py and connections/snowflake_connection.py
- whenever I mention duckDB, I mean the file called `benchmark_results.duckdb` in the project root.
- in duckdb, the schema we use is always benchmark_results.main
- if duckdb is locked when you try to use it, just stop and ask me to close it. Don't start doing crazy work arounds.
- after you write a bunch of python code, run `uvx ruff check --fix` to make sure unused imports and other linting issues are cleaned up. Please inspect the output of this command to see if there were any unfixable violations, and help fix them.

## Implementation Details

### Architecture Patterns
- **Separation of Concerns**: Benchmark modules are split into:
  - `warehouse_manager.py` - Warehouse lifecycle (create, destroy, suspend/resume)
  - `query_executor.py` - Query execution and metrics collection
  - `benchmark.py` - Orchestration using the managers
- **Scenario Support**: Warehouse names include scenario (`BENCHMARK_WH_XLARGE_NORMAL_001`) to prevent conflicts when running multiple scenarios with same run_id
- **Run Type Classification**: Queries are classified as `cold` (first), `semi-warm` (new query on warm warehouse), or `warm` (repeated query)

### Testing
- **Always run tests** after refactoring: `./run_tests.sh` or `uv run pytest tests/ -v`
- **Keep tests updated** when changing core logic (warehouse naming, scenario handling, run types)
- **Test coverage**: 34 tests covering warehouse managers, query executors, and scenario integration
- Tests use mocks - no database connections required

### Analysis (dbt)
- Run `uv run dbt build --profiles-dir .` in transformations directory to rebuild all views if needed. Views don't really need to be updated unless something in the sql chagned.