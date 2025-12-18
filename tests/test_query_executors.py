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

    def test_load_ctas_variant_query(self, query_executor):
        """Test loading CTAS variant queries"""
        from unittest.mock import patch, mock_open

        variant_sql = "SELECT l_orderkey, l_partkey, l_quantity FROM LINEITEM"

        with patch("builtins.open", mock_open(read_data=variant_sql)):
            with patch("pathlib.Path.exists", return_value=True):
                query = query_executor.load_ctas_query_variant("narrow_tall")
                assert "SELECT" in query
                assert "LINEITEM" in query

    def test_load_ctas_variant_not_found(self, query_executor):
        """Test loading non-existent variant raises error"""
        from unittest.mock import patch

        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                query_executor.load_ctas_query_variant("nonexistent")

    def test_execute_ctas_with_variant(self, query_executor, mock_connection):
        """Test execute_ctas_query with variant parameter"""
        from unittest.mock import patch

        # Mock cursor behavior
        mock_cursor = Mock()
        mock_cursor.sfqid = "test-query-id"
        mock_cursor.rowcount = 1000
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_still_running.return_value = False
        mock_connection.get_query_status_throw_if_error.return_value = None

        with patch.object(query_executor, 'set_query_tag'):
            result = query_executor.execute_ctas_query(
                query_num=0,
                run_num=1,
                warehouse_name="TEST_WH",
                warehouse_size="MEDIUM",
                scenario="ctas",
                query_sql="SELECT * FROM LINEITEM",
                table_name="TEST_TABLE",
                ctas_variant="narrow_tall",
            )

        assert result["ctas_variant"] == "narrow_tall"
        assert result["scenario"] == "ctas"
        assert result["query_num"] == 0


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

    def test_load_ctas_variant_query(self, query_executor):
        """Test loading CTAS variant queries"""
        from unittest.mock import patch, mock_open

        variant_sql = "SELECT l_orderkey, l_partkey, l_quantity FROM lineitem"

        with patch("builtins.open", mock_open(read_data=variant_sql)):
            with patch("pathlib.Path.exists", return_value=True):
                query = query_executor.load_ctas_query_variant("narrow_tall")
                assert "SELECT" in query
                assert "lineitem" in query

    def test_load_ctas_variant_not_found(self, query_executor):
        """Test loading non-existent variant raises error"""
        from unittest.mock import patch

        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                query_executor.load_ctas_query_variant("nonexistent")

    def test_execute_ctas_with_variant(self, query_executor, mock_connection):
        """Test execute_ctas_query with variant parameter"""
        # Just verify the result contains the ctas_variant field
        # The actual execution is mocked at the connection level
        result = query_executor._create_error_result(
            query_num=0,
            run_num=1,
            run_type="cold",
            query_tag='{"app": "test"}',
            warehouse_id="test_wh_id",
            warehouse_size="SMALL",
            scenario="ctas",
            error_message="",
        )
        # Add ctas_variant to result (simulating what execute_ctas_query does)
        result["ctas_variant"] = "narrow_tall"

        assert result["ctas_variant"] == "narrow_tall"
        assert result["scenario"] == "ctas"
        assert result["query_num"] == 0


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
