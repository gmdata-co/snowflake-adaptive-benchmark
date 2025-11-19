#!/bin/bash
# Test runner for Snowflake vs Databricks benchmark

set -e

echo "================================================"
echo "Running Benchmark Tests"
echo "================================================"
echo ""

# Run linter first
echo "🔍 Running linter..."
uvx ruff check --fix
echo "✅ Linter passed"
echo ""

# Run tests
echo "🧪 Running tests..."
uv run pytest tests/ -v --tb=short

echo ""
echo "================================================"
echo "✅ All tests passed!"
echo "================================================"
