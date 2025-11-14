-- ============================================================================
-- Snowflake vs Databricks Benchmarking Project Setup
-- ============================================================================
-- This script sets up the role, database, and warehouses for TPC-H SF1000
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
    COMMENT = 'Role for TPC-H SF1000 benchmarking project';

-- Grant benchmark role to SYSADMIN for management
GRANT ROLE BENCHMARK TO ROLE SYSADMIN;

-- ============================================================================
-- Step 2: Create BENCHMARK Database
-- ============================================================================

-- Switch to SYSADMIN to create database
USE ROLE SYSADMIN;

-- Create the benchmark database
CREATE DATABASE IF NOT EXISTS BENCHMARK
    COMMENT = 'Database for Snowflake vs Databricks TPC-H SF1000 benchmarking';

-- Grant all privileges on database to BENCHMARK role
GRANT ALL ON DATABASE BENCHMARK TO ROLE BENCHMARK;



-- ============================================================================
-- Step 3: Warehouse Management (Dynamic Creation)
-- ============================================================================
-- NOTE: Warehouses are now created dynamically by the benchmark script.
--
-- The benchmark script will:
-- 1. Create warehouses on-the-fly with run_id suffix (e.g., BENCHMARK_WH_MEDIUM_001)
-- 2. Use SYSADMIN role to create warehouses
-- 3. Grant ALL privileges on warehouses to BENCHMARK role
-- 4. Destroy warehouses at the end of the run for perfect cost attribution
--
-- Warehouse sizes used:
-- - SMALL: Budget comparison
-- - MEDIUM: Primary baseline
-- - XLARGE: Performance ceiling
--
-- Warehouse settings:
-- - AUTO_SUSPEND: 120 seconds (2 minutes)
-- - AUTO_RESUME: TRUE
-- - INITIALLY_SUSPENDED: TRUE
--
-- No manual warehouse creation is needed!
-- ============================================================================

-- ============================================================================
-- Step 4: Verify Access to Sample Data
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

-- Display setup summary
SELECT 'Setup complete. Ready for TPC-H benchmarking.' AS status;
SELECT 'Note: Warehouses will be created automatically by the benchmark script.' AS note;
