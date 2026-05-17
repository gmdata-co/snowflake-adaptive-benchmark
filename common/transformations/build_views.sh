#!/bin/bash
#
# Build all dbt views for benchmark analysis
#
# This script runs dbt to create all comparison views from the benchmark results.
# It should be run after benchmarks have completed to refresh the views.
#

set -e

# Get the directory where this script lives
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Building benchmark comparison views with dbt..."
echo "=============================================="
echo ""

# Change to transformations directory
cd "$SCRIPT_DIR"

# Run dbt build with the local profiles.yml
uv run dbt build --profiles-dir .

echo ""
echo "=============================================="
echo "Views created successfully!"
echo ""
echo "Query the views:"
echo "  duckdb ../../benchmark_results.duckdb -c 'SELECT * FROM adaptive_vs_gen1_summary;'"
echo ""
