# Databricks vs Snowflake Benchmarking Plan

## 1. Context from Industry Benchmarks

**Key Findings:**
- Most common scale: SF1000 (1TB) for practical comparisons
- TPC-H: 22 queries, 8 tables - simpler than TPC-DS (99 queries)
- Independent sources: [Fivetran (March 2025)](https://www.fivetran.com/blog/warehouse-benchmark), [Nitor Infotech](https://www.nitorinfotech.com/blog/snowflake-vs-databricks-sql-warehouse-a-deep-dive-into-performance-and-cost/)
- **Fivetran approach:** Did NOT use clustering keys or advanced features - focused on default performance
- Consensus: Near-tie on performance, Snowflake easier out-of-box, Databricks better for ML/complex workloads

**Critical Learnings:**
- Use pre-sorted data on both platforms for fair comparison (following Fivetran's approach)
- Clear result caches between runs
- Track cold vs warm runs separately
- Document query failures

---

## 2. Compute Size Equivalents

| Snowflake | Databricks Classic/Pro | Use Case |
|-----------|------------------------|----------|
| Small (S) | X-Small | Budget comparison |
| Medium (M) | Small | **Primary baseline** |
| X-Large (XL) | Large | Performance ceiling |

**Note:** Databricks Serverless most comparable to Snowflake's model (both fully managed).

---

## 3. Dataset: TPC-H SF1000 (1TB)

**Snowflake:** Pre-loaded at `SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000`
**Databricks:** Generate using [tpch-dbgen](https://github.com/databricks/tpch-dbgen) or [spark-sql-perf](https://github.com/databricks/spark-sql-perf), store in Delta Lake

---

## 4. Test Scenarios

### Scenario 1: Primary Comparison
**Snowflake:** Medium warehouse, SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000 (pre-sorted), auto-suspend 2 min
**Databricks:** Small SQL warehouse, Delta Lake with data pre-sorted (matching Snowflake's sort order)

**Test:** All 22 TPC-H queries × 4 runs (1 cold + 3 warm)

### Scenario 2: Concurrency (Optional)
**Test:** 5 queries (1,3,5,6,14) simultaneously with 3 warehouse sizes  
**Snowflake:** Single cluster vs multi-cluster (2-4)  
**Databricks:** Monitor autoscaling behavior

---

## 5. Recommended Warehouse Sizes for SF1000

| Test Purpose | Snowflake | Databricks | Why |
|--------------|-----------|------------|-----|
| **Primary** | Medium (M) | Small | Most common for 1TB, cost/performance balance |
| Budget | Small (S) | X-Small | Low-cost comparison |
| Performance | X-Large (XL) | Large | Best-case ceiling |

---

## 6. Cost & Duration Attribution

### Snowflake

**Query Tagging:**
```sql
ALTER SESSION SET QUERY_TAG = 'tpch_sf1000_primary_q01_run1';
-- Or: /* BENCHMARK: tpch_sf1000_primary_q01_run1 */
```

**Query History & Duration:**
```sql
SELECT
    query_id, query_tag, warehouse_name, warehouse_size,
    start_time, end_time,
    total_elapsed_time/1000 as execution_time_sec,
    compilation_time/1000 as compilation_sec,
    queued_provisioning_time/1000 as queue_sec,
    bytes_scanned, rows_produced,
    credits_used_cloud_services
FROM snowflake.account_usage.query_history
WHERE query_tag LIKE 'tpch_sf1000%'
ORDER BY start_time;
```

**Cost:**
```sql
SELECT warehouse_name, start_time, end_time,
    credits_used, credits_used_compute, credits_used_cloud_services
FROM snowflake.account_usage.warehouse_metering_history
WHERE warehouse_name = 'BENCHMARK_WH' AND start_time >= '2025-11-01';
```

**Formula:** `Query Cost = credits_used × credit_price` (typically $2-4/credit for Enterprise)

---

### Databricks

**Query Tagging:**
```sql
/* BENCHMARK: tpch_sf1000_primary_q01_run1 */
```

**Query History & Duration:**
```sql
SELECT statement_id, statement_text, warehouse_id, executed_by,
    start_time, end_time,
    duration as execution_time_ms,
    duration/1000.0 as execution_time_sec,
    rows_produced, read_bytes, bytes_produced,
    compute_time_ms, error_message
FROM system.query.history
WHERE statement_text LIKE '%BENCHMARK: tpch_sf1000%'
  AND start_time >= '2025-11-01'
ORDER BY start_time;
```

**Cost:**
```sql
SELECT usage_date,
    usage_metadata.warehouse_name,
    usage_metadata.statement_id,
    sku_name, usage_unit,
    usage_quantity as dbus_used,
    usage_quantity * list_price as estimated_cost,
    usage_start_time, usage_end_time
FROM system.billing.usage
WHERE usage_metadata.warehouse_name LIKE 'benchmark%'
  AND usage_date >= '2025-11-01'
ORDER BY usage_start_time;
```

**Formula:** `Query Cost = DBUs_used × DBU_price` (~$0.22-0.75/DBU depending on SKU)

---

### Key Metrics

**Duration:**
- Snowflake: `total_elapsed_time`, `execution_time`, `compilation_time`
- Databricks: `duration`, `compute_time_ms`

**Cost:**
- Snowflake: `credits_used` from metering_history
- Databricks: `usage_quantity` (DBUs) from billing.usage

**Comparison Metrics:**
- Cost per query: `total_cost / num_queries`
- Cost per second: `query_cost / execution_time_sec`
- Cost per GB scanned: `query_cost / (bytes_scanned/1e9)`

**Timing:** Wait 45+ min after Snowflake queries for ACCOUNT_USAGE updates; Databricks billing updates every few hours.

---

## 7. Time & Cost Estimates

| Phase | Time | Snowflake Cost | Databricks Cost |
|-------|------|----------------|-----------------|
| Setup (data gen, config) | 5-8 hrs | $10-20 | $60-120 |
| Scenario 1: Primary | 2-3 hrs | $40-80 | $60-120 |
| Scenario 2: Concurrency | 1-2 hrs | $30-60 | $30-60 |
| Analysis & docs | 4-8 hrs | - | - |
| **TOTAL** | **12-21 hrs** | **$80-160** | **$150-300** |

**Lean approach** (primary scenario only): $50-100 (Snowflake), $120-240 (Databricks)

---

## 8. Implementation Checklist

### Phase 1: Preparation
- [ ] Set up Databricks workspace
- [ ] Generate TPC-H SF1000 in Databricks with pre-sorting (Delta Lake)
- [ ] Validate Snowflake TPCH_SF1000 access
- [ ] Create warehouses with 2-min auto-suspend
- [ ] Prepare query scripts (22 TPC-H queries with tags)
- [ ] Set up result tracking spreadsheet

### Phase 2: Primary Testing
- [ ] Run cold + 3 warm iterations on both platforms
- [ ] Capture metrics from query_history tables
- [ ] Export results

### Phase 3: Concurrency Testing (Optional)
- [ ] Test multi-user scenarios (5 queries, 3 sizes)
- [ ] Compare autoscaling behavior

### Phase 4: Analysis
- [ ] Aggregate results by query, scenario, warehouse size
- [ ] Calculate cost metrics
- [ ] Create comparison charts
- [ ] Document findings

---

## 9. Key Gotchas

**Data:**
- ⚠️ Snowflake's `SNOWFLAKE_SAMPLE_DATA` is a read-only share (cannot modify)
- ✅ Pre-sort Databricks data to match Snowflake's ordering for fair comparison
- ⚠️ Databricks default sample is only 5GB (too small - use generated SF1000)
- ⚠️ Document data generation time/cost separately

**Execution:**
- ⚠️ Clear result cache: `ALTER SESSION SET USE_CACHED_RESULT = FALSE` (Snowflake)
- ⚠️ Disable Databricks result caching in warehouse settings
- ⚠️ Minor TPC-H query syntax adjustments may be needed

**Cost Tracking:**
- ✅ Tag ALL queries consistently: `tpch_sf1000_primary_q{##}_run{#}`
- ✅ Use ACCOUNT_USAGE for Snowflake (45 min delay)
- ✅ Export data immediately after each session

---

## 10. References

- [TPC-H Benchmark Spec](http://www.tpc.org/tpch/)
- [Snowflake TPC-H Sample Data](https://docs.snowflake.com/en/user-guide/sample-data-tpch)
- [Databricks tpch-dbgen](https://github.com/databricks/tpch-dbgen)
- [Databricks spark-sql-perf](https://github.com/databricks/spark-sql-perf)

---

**Document Status:** Draft v1.5 (Condensed for Claude Code)  
**Last Updated:** November 11, 2025  
**Owner:** Jeff  
**Changes in v1.5:**
- Simplified to focus on fair comparison (following Fivetran's approach)
- Removed clustering/optimization scenarios - both platforms use pre-sorted data
- Reduced to 2 scenarios: Primary comparison + optional concurrency
- Lowered cost estimates and simplified implementation