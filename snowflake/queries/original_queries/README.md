# Original TPC-H Queries

These are the original TPC-H benchmark queries (1.sql - 22.sql) generated using the TPC-H qgen tool.

## Source

These queries were generated from the official TPC-H benchmark specification and contain:
- Metadata lines (`:x`, `:o`, `:n`)
- Parameter placeholders (`:1`, `:2`, etc.)
- Generic table names without database/schema qualifiers
- Standard SQL syntax that may need adaptation for specific databases

## Processing

These files are processed by the `adapt_queries.py` script to create Snowflake-specific versions that are stored in the `adapted_queries` folder.
