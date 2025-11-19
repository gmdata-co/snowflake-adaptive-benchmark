#!/usr/bin/env python3
"""
Integration tests for scenario handling

These tests verify that the scenario refactor works end-to-end:
- Warehouse naming includes scenarios
- No naming conflicts between scenarios
- Scenario column is populated correctly
- Run IDs can be shared across scenarios
"""

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestScenarioWarehouseNaming:
    """Test that scenarios prevent warehouse naming conflicts"""

    def test_same_run_id_different_scenarios_no_conflict_snowflake(self):
        """Test same run_id with different scenarios creates unique warehouse names (Snowflake)"""
        from snowflake.warehouse_manager import WarehouseManager

        mock_conn = Mock()
        mock_conn.cursor.return_value = Mock()

        wm_normal = WarehouseManager(connection=mock_conn, run_id="001")
        wm_coldstart = WarehouseManager(connection=mock_conn, run_id="001")

        # Same size, same run_id, different scenarios
        normal_wh = wm_normal.get_warehouse_name("medium", "normal")
        coldstart_wh = wm_coldstart.get_warehouse_name("medium", "coldstart")

        # Names should be different!
        assert normal_wh != coldstart_wh
        assert normal_wh == "BENCHMARK_WH_MEDIUM_NORMAL_001"
        assert coldstart_wh == "BENCHMARK_WH_MEDIUM_COLDSTART_001"

    def test_same_run_id_different_scenarios_no_conflict_databricks(self):
        """Test same run_id with different scenarios creates unique warehouse names (Databricks)"""
        with patch('databricks.warehouse_manager.WorkspaceClient'):
            from databricks.warehouse_manager import WarehouseManager

            wm_normal = WarehouseManager(run_id="001")
            wm_coldstart = WarehouseManager(run_id="001")

            # Same size, same run_id, different scenarios
            normal_wh = wm_normal.get_warehouse_name("small", "normal")
            coldstart_wh = wm_coldstart.get_warehouse_name("small", "coldstart")

            # Names should be different!
            assert normal_wh != coldstart_wh
            assert normal_wh == "benchmark_dbx_small_normal_001"
            assert coldstart_wh == "benchmark_dbx_small_coldstart_001"

    def test_all_three_scenarios_unique_names_snowflake(self):
        """Test all three scenarios create unique warehouse names (Snowflake)"""
        from snowflake.warehouse_manager import WarehouseManager

        mock_conn = Mock()
        mock_conn.cursor.return_value = Mock()

        wm = WarehouseManager(connection=mock_conn, run_id="001")

        normal_wh = wm.get_warehouse_name("medium", "normal")
        coldstart_wh = wm.get_warehouse_name("medium", "coldstart")
        concurrent_wh = wm.get_warehouse_name("medium", "concurrent")

        # All three should be different
        assert len({normal_wh, coldstart_wh, concurrent_wh}) == 3
        assert "NORMAL" in normal_wh
        assert "COLDSTART" in coldstart_wh
        assert "CONCURRENT" in concurrent_wh

    def test_all_three_scenarios_unique_names_databricks(self):
        """Test all three scenarios create unique warehouse names (Databricks)"""
        with patch('databricks.warehouse_manager.WorkspaceClient'):
            from databricks.warehouse_manager import WarehouseManager

            wm = WarehouseManager(run_id="001")

            normal_wh = wm.get_warehouse_name("small", "normal")
            coldstart_wh = wm.get_warehouse_name("small", "coldstart")
            concurrent_wh = wm.get_warehouse_name("small", "concurrent")

            # All three should be different
            assert len({normal_wh, coldstart_wh, concurrent_wh}) == 3
            assert "normal" in normal_wh
            assert "coldstart" in coldstart_wh
            assert "concurrent" in concurrent_wh


class TestScenarioInResults:
    """Test that scenario is properly included in results"""

    def test_scenario_in_snowflake_result(self):
        """Test scenario appears in Snowflake query results"""
        from snowflake.query_executor import QueryExecutor

        mock_conn = Mock()
        mock_storage = Mock()

        executor = QueryExecutor(
            connection=mock_conn,
            storage=mock_storage,
            run_id="001",
            scale_factor=1000,
        )

        # Test normal scenario
        error_result = executor._create_error_result(
            query_num=1,
            run_num=1,
            run_type="cold",
            query_tag="{}",
            warehouse_name="test_wh",
            warehouse_size="MEDIUM",
            scenario="normal",
            error_message="test"
        )
        assert error_result["scenario"] == "normal"

        # Test coldstart scenario
        error_result = executor._create_error_result(
            query_num=1,
            run_num=1,
            run_type="cold",
            query_tag="{}",
            warehouse_name="test_wh",
            warehouse_size="MEDIUM",
            scenario="coldstart",
            error_message="test"
        )
        assert error_result["scenario"] == "coldstart"

    def test_scenario_in_databricks_result(self):
        """Test scenario appears in Databricks query results"""
        from databricks.query_executor import QueryExecutor

        mock_conn = Mock()
        mock_storage = Mock()

        executor = QueryExecutor(
            connection=mock_conn,
            storage=mock_storage,
            run_id="001",
            scale_factor=1000,
        )

        # Test normal scenario
        error_result = executor._create_error_result(
            query_num=1,
            run_num=1,
            run_type="cold",
            query_tag="{}",
            warehouse_id="test_wh_id",
            warehouse_size="SMALL",
            scenario="normal",
            error_message="test"
        )
        assert error_result["scenario"] == "normal"

        # Test coldstart scenario
        error_result = executor._create_error_result(
            query_num=1,
            run_num=1,
            run_type="cold",
            query_tag="{}",
            warehouse_id="test_wh_id",
            warehouse_size="SMALL",
            scenario="coldstart",
            error_message="test"
        )
        assert error_result["scenario"] == "coldstart"


class TestRunIdSharing:
    """Test that run_id can be shared across scenarios"""

    def test_snowflake_benchmark_accepts_run_id(self):
        """Test SnowflakeBenchmark accepts and uses provided run_id"""
        from snowflake.benchmark import SnowflakeBenchmark

        # Should use provided run_id
        benchmark = SnowflakeBenchmark(run_id="999")
        assert benchmark.run_id == "999"

    def test_databricks_benchmark_accepts_run_id(self):
        """Test DatabricksBenchmark accepts and uses provided run_id"""
        from databricks.benchmark import DatabricksBenchmark

        # Should use provided run_id
        benchmark = DatabricksBenchmark(run_id="999")
        assert benchmark.run_id == "999"

    def test_multiple_benchmarks_share_run_id(self):
        """Test multiple benchmark instances can share same run_id"""
        from snowflake.benchmark import SnowflakeBenchmark
        from databricks.benchmark import DatabricksBenchmark

        shared_run_id = "777"

        sf_benchmark = SnowflakeBenchmark(run_id=shared_run_id)
        dbx_benchmark = DatabricksBenchmark(run_id=shared_run_id)

        assert sf_benchmark.run_id == shared_run_id
        assert dbx_benchmark.run_id == shared_run_id
        assert sf_benchmark.run_id == dbx_benchmark.run_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
