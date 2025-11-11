-- ============================================================================
-- Snowflake vs Databricks Benchmarking Project Setup
-- ============================================================================
-- This script sets up the role, database, and warehouses for TPC-H SF100
-- benchmarking according to the project plan requirements.
--
-- Requirements:
-- - Create BENCHMARK role and grant to SYSADMIN
-- - Create BENCHMARK database owned by SYSADMIN
-- - Create warehouses (Small, Medium, X-Large) with 2-min auto-suspend
-- - Grant appropriate permissions
-- ============================================================================


USE ROLE accountadmin;

-- ============================================================================
-- Step 1: Create and Configure BENCHMARK Role
-- ============================================================================

-- Create the benchmark role
CREATE ROLE IF NOT EXISTS BENCHMARK
    COMMENT = 'Role for TPC-H SF100 benchmarking project';

-- Grant benchmark role to SYSADMIN for management
GRANT ROLE BENCHMARK TO ROLE SYSADMIN;

-- ============================================================================
-- Step 2: Create BENCHMARK Database
-- ============================================================================

-- Switch to SYSADMIN to create database
USE ROLE SYSADMIN;

-- Create the benchmark database
CREATE DATABASE IF NOT EXISTS BENCHMARK
    COMMENT = 'Database for Snowflake vs Databricks TPC-H SF100 benchmarking';

-- Grant all privileges on database to BENCHMARK role
GRANT ALL ON DATABASE BENCHMARK TO ROLE BENCHMARK;



-- ============================================================================
-- Step 3: Create Warehouses for Benchmarking
-- ============================================================================
-- Based on project plan Section 5: Small, Medium, X-Large
-- All warehouses have 2-min auto-suspend per Section 4 requirements
-- ============================================================================

-- Warehouse 1: SMALL (Budget comparison)
CREATE WAREHOUSE IF NOT EXISTS BENCHMARK_WH_SMALL
    WITH
    WAREHOUSE_SIZE = 'SMALL'
    AUTO_SUSPEND = 120  -- 2 minutes
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Small warehouse for budget comparison (SF100 TPC-H)';

-- Warehouse 2: MEDIUM (Primary baseline)
CREATE WAREHOUSE IF NOT EXISTS BENCHMARK_WH_MEDIUM
    WITH
    WAREHOUSE_SIZE = 'MEDIUM'
    AUTO_SUSPEND = 120  -- 2 minutes
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Medium warehouse for primary baseline testing (SF100 TPC-H)';

-- Warehouse 3: X-LARGE (Performance ceiling)
CREATE WAREHOUSE IF NOT EXISTS BENCHMARK_WH_XLARGE
    WITH
    WAREHOUSE_SIZE = 'X-LARGE'
    AUTO_SUSPEND = 120  -- 2 minutes
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'X-Large warehouse for performance ceiling testing (SF100 TPC-H)';

-- ============================================================================
-- Step 4: Grant Warehouse Permissions to BENCHMARK Role
-- ============================================================================

-- Grant all privileges on each warehouse to BENCHMARK role
GRANT ALL ON WAREHOUSE BENCHMARK_WH_SMALL TO ROLE BENCHMARK;
GRANT ALL ON WAREHOUSE BENCHMARK_WH_MEDIUM TO ROLE BENCHMARK;
GRANT ALL ON WAREHOUSE BENCHMARK_WH_XLARGE TO ROLE BENCHMARK;

-- ============================================================================
-- Step 5: Verify Access to Sample Data
-- ============================================================================

-- Grant usage on SNOWFLAKE_SAMPLE_DATA to BENCHMARK role
use role accountadmin;
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE_SAMPLE_DATA TO ROLE BENCHMARK;

GRANT IMPORTED PRIVILEGES ON DATABASE snowflake TO ROLE BENCHMARK;

-- ============================================================================
-- Setup Complete
-- ============================================================================

-- Switch to BENCHMARK role to verify setup
USE ROLE BENCHMARK;
USE DATABASE BENCHMARK;
USE WAREHOUSE BENCHMARK_WH_MEDIUM;

-- Verify access to TPC-H SF100 sample data
SELECT COUNT(*) AS lineitem_row_count
FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.LINEITEM;

-- Display setup summary
SELECT 'Setup complete. Ready for TPC-H SF100 benchmarking.' AS status;
