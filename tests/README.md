# Benchmark Tests

Comprehensive test suite for the Snowflake vs Databricks benchmark refactor.

## Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_warehouse_managers.py -v

# Run tests with coverage
uv run pytest tests/ --cov=snowflake --cov=databricks -v

# Run tests matching a pattern
uv run pytest tests/ -k "warehouse_naming" -v
```

## Test Files

### `test_warehouse_managers.py`
Tests for warehouse lifecycle management:
- ✅ Warehouse naming with scenarios (normal, coldstart, concurrent)
- ✅ Warehouse naming with different run IDs
- ✅ Warehouse naming with different sizes
- ✅ Warehouse creation tracking for cleanup
- ✅ Warehouse map generation

### `test_query_executors.py`
Tests for query execution logic:
- ✅ Run type determination (cold, semi-warm, warm)
- ✅ Force run type override
- ✅ Warehouse state tracking
- ✅ Independent state per warehouse
- ✅ Scenario handling in results

### `test_scenario_integration.py`
Integration tests for scenario handling:
- ✅ No warehouse naming conflicts between scenarios
- ✅ All three scenarios create unique names
- ✅ Scenario appears in query results
- ✅ Run ID sharing across scenarios
- ✅ Multiple benchmarks can share run_id

## What These Tests Verify

### 1. Warehouse Naming (Critical)
The refactor includes scenario in warehouse names to prevent conflicts:
- `BENCHMARK_WH_MEDIUM_NORMAL_001` ✅
- `BENCHMARK_WH_MEDIUM_COLDSTART_001` ✅
- No more naming collisions when running multiple scenarios!

### 2. Scenario Tracking (Critical)
Each result includes the scenario it belongs to:
- `scenario = "normal"` for regular benchmarks
- `scenario = "coldstart"` for cold start trials
- `scenario = "concurrent"` ready for future

### 3. Run Type Classification (Important)
Query execution correctly classifies run types:
- First query on warehouse = `cold`
- New query on warm warehouse = `semi-warm`
- Repeated query = `warm`
- Force override works for cold start trials

### 4. Run ID Sharing (Critical)
Multiple scenarios can share the same run_id:
- Enables direct comparison in DuckDB
- `--scenario all` uses one run_id for both scenarios

## Test Coverage

**34 tests** covering:
- Snowflake WarehouseManager (7 tests)
- Databricks WarehouseManager (6 tests)
- Snowflake QueryExecutor (6 tests)
- Databricks QueryExecutor (4 tests)
- Scenario handling (2 tests)
- Integration scenarios (9 tests)

All tests use mocks - **no actual database connections required!**

## Adding New Tests

When adding new functionality:

1. Add tests to appropriate file
2. Use mocks to avoid real connections
3. Test both Snowflake and Databricks versions
4. Verify scenario handling
5. Run tests before committing

Example:
```python
def test_new_feature(self, mock_connection, mock_storage):
    """Test description"""
    executor = QueryExecutor(
        connection=mock_connection,
        storage=mock_storage,
        run_id="001",
        scale_factor=1000,
    )

    result = executor.new_feature()
    assert result == expected_value
```
