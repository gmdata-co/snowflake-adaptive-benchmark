#!/usr/bin/env python3
"""
Unit tests for WarehouseManager classes

These tests verify warehouse naming, lifecycle operations, and scenario handling
without requiring actual database connections.
"""

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from snowflake.warehouse_manager import WarehouseManager as SnowflakeWarehouseManager
from databricks.warehouse_manager import WarehouseManager as DatabricksWarehouseManager


class TestSnowflakeWarehouseManager:
    """Test Snowflake WarehouseManager"""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Snowflake connection"""
        connection = Mock()
        connection.cursor.return_value = Mock()
        return connection

    @pytest.fixture
    def warehouse_manager(self, mock_connection):
        """Create WarehouseManager instance with mock connection"""
        return SnowflakeWarehouseManager(connection=mock_connection, run_id="001")

    def test_warehouse_naming_normal_scenario(self, warehouse_manager):
        """Test warehouse name includes scenario: normal"""
        name = warehouse_manager.get_warehouse_name("large", "normal")
        assert name == "BENCHMARK_WH_LARGE_NORMAL_001"

    def test_warehouse_naming_coldstart_scenario(self, warehouse_manager):
        """Test warehouse name includes scenario: coldstart"""
        name = warehouse_manager.get_warehouse_name("large", "coldstart")
        assert name == "BENCHMARK_WH_LARGE_COLDSTART_001"

    def test_warehouse_naming_concurrent_scenario(self, warehouse_manager):
        """Test warehouse name includes scenario: concurrent"""
        name = warehouse_manager.get_warehouse_name("xlarge", "concurrent")
        assert name == "BENCHMARK_WH_XLARGE_CONCURRENT_001"

    def test_warehouse_naming_different_sizes(self, warehouse_manager):
        """Test warehouse naming with different sizes"""
        assert warehouse_manager.get_warehouse_name("medium", "normal") == "BENCHMARK_WH_MEDIUM_NORMAL_001"
        assert warehouse_manager.get_warehouse_name("large", "normal") == "BENCHMARK_WH_LARGE_NORMAL_001"
        assert warehouse_manager.get_warehouse_name("xlarge", "normal") == "BENCHMARK_WH_XLARGE_NORMAL_001"

    def test_warehouse_naming_different_run_ids(self, mock_connection):
        """Test warehouse naming with different run IDs"""
        wm1 = SnowflakeWarehouseManager(connection=mock_connection, run_id="001")
        wm2 = SnowflakeWarehouseManager(connection=mock_connection, run_id="002")
        wm3 = SnowflakeWarehouseManager(connection=mock_connection, run_id="123")

        assert wm1.get_warehouse_name("large", "normal") == "BENCHMARK_WH_LARGE_NORMAL_001"
        assert wm2.get_warehouse_name("large", "normal") == "BENCHMARK_WH_LARGE_NORMAL_002"
        assert wm3.get_warehouse_name("large", "normal") == "BENCHMARK_WH_LARGE_NORMAL_123"

    def test_create_warehouse_tracks_for_cleanup(self, warehouse_manager, mock_connection):
        """Test that created warehouses are tracked for cleanup"""
        warehouse_name = warehouse_manager.create_warehouse("large", "normal")
        assert warehouse_name in warehouse_manager.created_warehouses

    def test_create_all_warehouses_returns_map(self, warehouse_manager):
        """Test create_all_warehouses returns size -> name mapping"""
        sizes = ["medium", "large", "xlarge"]
        warehouse_map = warehouse_manager.create_all_warehouses(sizes, "normal")

        assert len(warehouse_map) == 3
        assert warehouse_map["medium"] == "BENCHMARK_WH_MEDIUM_NORMAL_001"
        assert warehouse_map["large"] == "BENCHMARK_WH_LARGE_NORMAL_001"
        assert warehouse_map["xlarge"] == "BENCHMARK_WH_XLARGE_NORMAL_001"


class TestDatabricksWarehouseManager:
    """Test Databricks WarehouseManager"""

    @pytest.fixture
    def warehouse_manager(self):
        """Create WarehouseManager instance"""
        with patch('databricks.warehouse_manager.WorkspaceClient'):
            return DatabricksWarehouseManager(run_id="001")

    def test_warehouse_naming_normal_scenario(self, warehouse_manager):
        """Test warehouse name includes scenario: normal"""
        name = warehouse_manager.get_warehouse_name("medium", "normal")
        assert name == "benchmark_dbx_medium_normal_001"

    def test_warehouse_naming_coldstart_scenario(self, warehouse_manager):
        """Test warehouse name includes scenario: coldstart"""
        name = warehouse_manager.get_warehouse_name("medium", "coldstart")
        assert name == "benchmark_dbx_medium_coldstart_001"

    def test_warehouse_naming_concurrent_scenario(self, warehouse_manager):
        """Test warehouse name includes scenario: concurrent"""
        name = warehouse_manager.get_warehouse_name("large", "concurrent")
        assert name == "benchmark_dbx_large_concurrent_001"

    def test_warehouse_naming_different_sizes(self, warehouse_manager):
        """Test warehouse naming with different sizes"""
        assert warehouse_manager.get_warehouse_name("small", "normal") == "benchmark_dbx_small_normal_001"
        assert warehouse_manager.get_warehouse_name("medium", "normal") == "benchmark_dbx_medium_normal_001"
        assert warehouse_manager.get_warehouse_name("large", "normal") == "benchmark_dbx_large_normal_001"

    def test_warehouse_naming_different_run_ids(self):
        """Test warehouse naming with different run IDs"""
        with patch('databricks.warehouse_manager.WorkspaceClient'):
            wm1 = DatabricksWarehouseManager(run_id="001")
            wm2 = DatabricksWarehouseManager(run_id="002")
            wm3 = DatabricksWarehouseManager(run_id="456")

            assert wm1.get_warehouse_name("medium", "normal") == "benchmark_dbx_medium_normal_001"
            assert wm2.get_warehouse_name("medium", "normal") == "benchmark_dbx_medium_normal_002"
            assert wm3.get_warehouse_name("medium", "normal") == "benchmark_dbx_medium_normal_456"

    def test_create_warehouse_tracks_for_cleanup(self, warehouse_manager):
        """Test that created warehouses are tracked for cleanup"""
        # Mock the warehouse creation
        mock_warehouse = Mock()
        mock_warehouse.id = "test-warehouse-id"
        warehouse_manager.workspace_client.warehouses.create.return_value = mock_warehouse

        warehouse_manager.create_warehouse("medium", "normal")

        assert len(warehouse_manager.created_warehouses) == 1
        assert warehouse_manager.created_warehouses[0]["id"] == "test-warehouse-id"
        assert warehouse_manager.created_warehouses[0]["size"] == "medium"
        assert warehouse_manager.created_warehouses[0]["name"] == "benchmark_dbx_medium_normal_001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
