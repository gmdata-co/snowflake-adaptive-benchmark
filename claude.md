# Snwoflake vs Databricks Performance Comparison

## Groundrules

- This project uses uv. Do not use the uv pip wrapper, only use uv native commands like uv add.
- always run python using uv run commands. no need to activate a venv.
- Use the snowflake CLI `snow` to run test queries or to do any setup. For example, if you need to figure out if your suggested SQL is valid, just run it real quick using `snow sql -q ...`
- when using the snowflake cli, ensure that `--connection demo` flag is used.
- the goal is to create a python file that will run multiple queries against snowflake and databricks.
- the overall project plan is at `project_plan.md`.
- dbx is short for databricks.