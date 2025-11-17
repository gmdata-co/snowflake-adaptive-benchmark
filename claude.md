# Snwoflake vs Databricks Performance Comparison

## Groundrules

- This project uses uv. Do not use the uv pip wrapper, only use uv native commands like uv add.
- always run python using uv run commands. no need to activate a venv.
- use the logging module instead of `print()`
- Use the snowflake CLI `snow` to run test queries or to do any setup. For example, if you need to figure out if your suggested SQL is valid, just run it real quick using `snow sql -q ...`
- when using the snowflake cli, use the `--connection` flag with the value specified in the `.env` file's `SNOWFLAKE_CONNECTION` variable.
- the goal is to create a python file that will run multiple queries against snowflake and databricks.
- the overall project plan is at `project_plan.md`.
- dbx is short for databricks.
- run `source ~/.zshrc` to get the databricks credentials loaded.
- any time you need to connect to snowflake or dbx with python, use the global connections modules in the common folder: connections/databricks_connection.py and connections/snowflake_connection.py