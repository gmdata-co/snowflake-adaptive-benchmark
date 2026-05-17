```
    _       _             _   _           ____                  _
   / \   __| | __ _ _ __ | |_(_)_   _____| __ )  ___ _ __   ___| |__
  / _ \ / _` |/ _` | '_ \| __| \ \ / / _ \  _ \ / _ \ '_ \ / __| '_ \
 / ___ \ (_| | (_| | |_) | |_| |\ V /  __/ |_) |  __/ | | | (__| | | |
/_/   \_\__,_|\__,_| .__/ \__|_| \_/ \___|____/ \___|_| |_|\___|_| |_|
                   |_|   Snowflake Adaptive vs Gen1 — TPC-H benchmark
```

# Snowflake Adaptive Benchmark

Welcome! 👋 This is a small, focused benchmark that answers one question:

> **Snowflake's new Adaptive Warehouse vs. classic Gen1 warehouses — which is faster, and which is cheaper?**

It runs the TPC-H SF1000 (1 TB) workload across four scenarios (single query,
sequential, concurrent, DML) and every warehouse size (XS → XL), captures real
credit cost from `ACCOUNT_USAGE`, and renders the whole story as an interactive
article.

## How it works

```
run_3track.sh ──┬─ adaptive      (per-query billed)        ┐
                ├─ gen1 + tail   (idle auto-suspend tail)   ├─ merge → enrich
                └─ gen1, no tail (killed at workload end)    ┘   → dbt → viz
```

Three isolated tracks run concurrently on uniquely-named warehouses, each
writing its own DuckDB. They're merged, enriched from `ACCOUNT_USAGE`,
transformed by a single dbt model (`adaptive_vs_gen1_summary`), and published
to the React app in `visualization/`.

## Quick start

```bash
uv sync                       # install deps
uv run setup_config.py        # generate .env (Snowflake connection)
./run_3track.sh               # run the full benchmark (long-running; use nohup)
cd visualization && npm install && npm run dev   # view the article
```

## Layout

| Path | What |
|------|------|
| `snowflake/` | benchmark execution (warehouses, queries, enrichment) |
| `common/` | DuckDB storage + dbt transformations |
| `visualization/` | the React article |
| `run_3track.sh`, `merge_tracks.py` | 3-track orchestration |

## Credits

Forked from [get-select/snowflake-databricks-benchmark](https://github.com/get-select/snowflake-databricks-benchmark)
by [SELECT](https://select.dev). This fork removes the Databricks side and
refocuses entirely on the Snowflake Adaptive-vs-Gen1 comparison.
