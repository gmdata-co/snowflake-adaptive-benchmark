#!/usr/bin/env python3
"""
Unit tests for QueryExecutor classes

These tests verify query execution logic, run type determination,
and result formatting without requiring actual database connections.
"""

import pytest
from unittest.mock import Mock
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from snowflake.query_executor import QueryExecutor as SnowflakeQueryExecutor
from databricks.query_executor import QueryExecutor as DatabricksQueryExecutor


class TestSnowflakeQueryExecutor:
    """Test Snowflake QueryExecutor"""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Snowflake connection"""
        connection = Mock()
        connection.cursor.return_value = Mock()
        return connection

    @pytest.fixture
    def mock_storage(self):
        """Create a mock BenchmarkStorage"""
        return Mock()

    @pytest.fixture
    def query_executor(self, mock_connection, mock_storage):
        """Create QueryExecutor instance"""
        return SnowflakeQueryExecutor(
            connection=mock_connection,
            storage=mock_storage,
            run_id="001",
            scale_factor=1000,
        )

    def test_run_type_first_query_is_cold(self, query_executor):
        """Test first query on a warehouse is classified as cold"""
        run_type = query_executor.determine_run_type(1, "warehouse_1")
        assert run_type == "cold"

    def test_run_type_new_query_is_semi_warm(self, query_executor):
        """Test new query on warm warehouse is semi-warm"""
        # First query - cold
        query_executor.execute_query = Mock(return_value={})
        query_executor.warehouse_states["warehouse_1"] = {
            "started": True,
            "queries_executed": {1}
        }

        # Second query (different number) - semi-warm
        run_type = query_executor.determine_run_type(2, "warehouse_1")
        assert run_type == "semi-warm"

    def test_run_type_repeated_query_is_warm(self, query_executor):
        """Test repeated query on warm warehouse is warm"""
        # Setup warehouse state: started, query 1 already executed
        query_executor.warehouse_states["warehouse_1"] = {
            "started": True,
            "queries_executed": {1}
        }

        # Run query 1 again - warm
        run_type = query_executor.determine_run_type(1, "warehouse_1")
        assert run_type == "warm"

    def test_force_run_type_overrides_detection(self, query_executor):
        """Test force_run_type parameter overrides automatic detection"""
        # Setup warm warehouse
        query_executor.warehouse_states["warehouse_1"] = {
            "started": True,
            "queries_executed": {1}
        }

        # Force cold even though it would be warm
        run_type = query_executor.determine_run_type(1, "warehouse_1", force_run_type="cold")
        assert run_type == "cold"

    def test_reset_warehouse_state(self, query_executor):
        """Test resetting warehouse state"""
        # Setup state
        query_executor.warehouse_states["warehouse_1"] = {
            "started": True,
            "queries_executed": {1, 2, 3}
        }

        # Reset
        query_executor.reset_warehouse_state("warehouse_1")

        # Verify state is reset
        assert "warehouse_1" not in query_executor.warehouse_states

    def test_different_warehouses_independent_state(self, query_executor):
        """Test different warehouses maintain independent state"""
        # Query 1 on warehouse_1 (cold)
        run_type_1 = query_executor.determine_run_type(1, "warehouse_1")
        assert run_type_1 == "cold"

        # Mark warehouse_1 as started
        query_executor.warehouse_states["warehouse_1"]["started"] = True
        query_executor.warehouse_states["warehouse_1"]["queries_executed"].add(1)

        # Query 1 on warehouse_2 should still be cold
        run_type_2 = query_executor.determine_run_type(1, "warehouse_2")
        assert run_type_2 == "cold"


class TestDatabricksQueryExecutor:
    """Test Databricks QueryExecutor"""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Databricks connection"""
        connection = Mock()
        connection.cursor.return_value = Mock()
        return connection

    @pytest.fixture
    def mock_storage(self):
        """Create a mock BenchmarkStorage"""
        return Mock()

    @pytest.fixture
    def query_executor(self, mock_connection, mock_storage):
        """Create QueryExecutor instance"""
        return DatabricksQueryExecutor(
            connection=mock_connection,
            storage=mock_storage,
            run_id="001",
            scale_factor=1000,
        )

    def test_run_type_first_query_is_cold(self, query_executor):
        """Test first query on a warehouse is classified as cold"""
        run_type = query_executor.determine_run_type(1, "warehouse_id_1")
        assert run_type == "cold"

    def test_run_type_new_query_is_semi_warm(self, query_executor):
        """Test new query on warm warehouse is semi-warm"""
        # Setup warehouse state: started, query 1 already executed
        query_executor.warehouse_states["warehouse_id_1"] = {
            "started": True,
            "queries_executed": {1}
        }

        # Second query (different number) - semi-warm
        run_type = query_executor.determine_run_type(2, "warehouse_id_1")
        assert run_type == "semi-warm"

    def test_run_type_repeated_query_is_warm(self, query_executor):
        """Test repeated query on warm warehouse is warm"""
        # Setup warehouse state: started, query 1 already executed
        query_executor.warehouse_states["warehouse_id_1"] = {
            "started": True,
            "queries_executed": {1}
        }

        # Run query 1 again - warm
        run_type = query_executor.determine_run_type(1, "warehouse_id_1")
        assert run_type == "warm"

    def test_force_run_type_overrides_detection(self, query_executor):
        """Test force_run_type parameter overrides automatic detection"""
        # Setup warm warehouse
        query_executor.warehouse_states["warehouse_id_1"] = {
            "started": True,
            "queries_executed": {1}
        }

        # Force cold even though it would be warm
        run_type = query_executor.determine_run_type(1, "warehouse_id_1", force_run_type="cold")
        assert run_type == "cold"


class TestScenarioHandling:
    """Test scenario handling across both platforms"""

    def test_snowflake_scenario_in_error_result(self):
        """Test scenario is included in error results (Snowflake)"""
        mock_connection = Mock()
        mock_storage = Mock()
        executor = SnowflakeQueryExecutor(
            connection=mock_connection,
            storage=mock_storage,
            run_id="001",
            scale_factor=1000,
        )

        error_result = executor._create_error_result(
            query_num=1,
            run_num=1,
            run_type="cold",
            query_tag='{"app": "test"}',
            warehouse_name="test_wh",
            warehouse_size="MEDIUM",
            scenario="coldstart",
            error_message="Test error"
        )

        assert error_result["scenario"] == "coldstart"
        assert error_result["platform"] == "snowflake"

    def test_databricks_scenario_in_error_result(self):
        """Test scenario is included in error results (Databricks)"""
        mock_connection = Mock()
        mock_storage = Mock()
        executor = DatabricksQueryExecutor(
            connection=mock_connection,
            storage=mock_storage,
            run_id="001",
            scale_factor=1000,
        )

        error_result = executor._create_error_result(
            query_num=1,
            run_num=1,
            run_type="cold",
            query_tag='{"app": "test"}',
            warehouse_id="test_wh_id",
            warehouse_size="SMALL",
            scenario="normal",
            error_message="Test error"
        )

        assert error_result["scenario"] == "normal"
        assert error_result["platform"] == "databricks"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
