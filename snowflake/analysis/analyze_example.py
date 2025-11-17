#!/usr/bin/env python3
"""
Example of using the BenchmarkAnalyzer as a library for custom analysis.

This script demonstrates how to:
1. Load benchmark results
2. Run built-in analyses
3. Execute custom SQL queries
4. Generate insights programmatically
"""

import logging
from analyze_results import BenchmarkAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main():
    """Demonstrate custom analysis using the BenchmarkAnalyzer."""

    # Initialize analyzer
    analyzer = BenchmarkAnalyzer("../results/benchmark_results.csv")

    logger.info("=" * 80)
    logger.info("CUSTOM BENCHMARK ANALYSIS EXAMPLE")
    logger.info("=" * 80 + "\n")

    # Example 1: Find queries with poor scaling to larger warehouses
    logger.info("\n1. QUERIES WITH POOR SCALING (slower on XLARGE vs MEDIUM)")
    logger.info("-" * 80)
    poor_scaling = analyzer.conn.execute("""
        SELECT
            query_num,
            ROUND(AVG(CASE WHEN warehouse_size='MEDIUM' THEN execution_time_sec END), 3) as medium,
            ROUND(AVG(CASE WHEN warehouse_size='XLARGE' THEN execution_time_sec END), 3) as xlarge,
            ROUND(AVG(CASE WHEN warehouse_size='XLARGE' THEN execution_time_sec END) -
                  AVG(CASE WHEN warehouse_size='MEDIUM' THEN execution_time_sec END), 3) as slowdown
        FROM benchmark_results
        WHERE run_type='warm'
        GROUP BY query_num
        HAVING xlarge > medium
        ORDER BY slowdown DESC
    """).fetchdf()

    if not poor_scaling.empty:
        logger.info(f"\nFound {len(poor_scaling)} queries that are slower on XLARGE:")
        logger.info(poor_scaling.to_string(index=False))
        logger.info(
            "\n⚠️  These queries may have bottlenecks that prevent scaling with compute."
        )
    else:
        logger.info("✅ All queries scale well with larger warehouse sizes.")

    # Example 2: Identify high-variance queries (inconsistent performance)
    logger.info("\n\n2. QUERIES WITH INCONSISTENT PERFORMANCE (high variance)")
    logger.info("-" * 80)
    high_variance = analyzer.conn.execute("""
        SELECT
            query_num,
            warehouse_size,
            ROUND(STDDEV(execution_time_sec), 3) as stddev,
            ROUND(AVG(execution_time_sec), 3) as avg_time,
            ROUND(STDDEV(execution_time_sec) / AVG(execution_time_sec) * 100, 1) as cv_pct
        FROM benchmark_results
        WHERE run_type='warm'
        GROUP BY query_num, warehouse_size
        HAVING cv_pct > 10
        ORDER BY cv_pct DESC
        LIMIT 10
    """).fetchdf()

    logger.info("\nTop queries with high coefficient of variation (CV > 10%):")
    logger.info(high_variance.to_string(index=False))
    logger.info("\n💡 High CV indicates unpredictable performance. Consider:")
    logger.info("   - Checking for concurrent workload interference")
    logger.info("   - Reviewing query plans for non-deterministic operations")
    logger.info("   - Investigating resource contention")

    # Example 3: ROI Analysis - Best candidates for XLARGE warehouse
    logger.info("\n\n3. BEST ROI FOR XLARGE WAREHOUSE (biggest speedup)")
    logger.info("-" * 80)
    roi_analysis = analyzer.conn.execute("""
        SELECT
            query_num,
            ROUND(AVG(CASE WHEN warehouse_size='MEDIUM' THEN execution_time_sec END), 3) as medium_time,
            ROUND(AVG(CASE WHEN warehouse_size='XLARGE' THEN execution_time_sec END), 3) as xlarge_time,
            ROUND(AVG(CASE WHEN warehouse_size='MEDIUM' THEN execution_time_sec END) -
                  AVG(CASE WHEN warehouse_size='XLARGE' THEN execution_time_sec END), 3) as time_saved,
            ROUND((AVG(CASE WHEN warehouse_size='MEDIUM' THEN execution_time_sec END) -
                   AVG(CASE WHEN warehouse_size='XLARGE' THEN execution_time_sec END)) /
                  AVG(CASE WHEN warehouse_size='MEDIUM' THEN execution_time_sec END) * 100, 1) as speedup_pct
        FROM benchmark_results
        WHERE run_type='warm'
        GROUP BY query_num
        HAVING time_saved > 0
        ORDER BY time_saved DESC
        LIMIT 10
    """).fetchdf()

    logger.info("\nTop 10 queries that benefit most from XLARGE warehouse:")
    logger.info(roi_analysis.to_string(index=False))
    logger.info(
        "\n💰 Consider running these queries on XLARGE for production workloads"
    )

    # Example 4: Quick wins - queries fast enough for real-time dashboards
    logger.info("\n\n4. REAL-TIME DASHBOARD CANDIDATES (< 3 seconds)")
    logger.info("-" * 80)
    fast_queries = analyzer.conn.execute("""
        SELECT
            query_num,
            ROUND(AVG(execution_time_sec), 3) as avg_time,
            ROUND(MAX(execution_time_sec), 3) as max_time,
            warehouse_size
        FROM benchmark_results
        WHERE run_type='warm'
        GROUP BY query_num, warehouse_size
        HAVING avg_time < 3
        ORDER BY warehouse_size, avg_time
    """).fetchdf()

    logger.info(
        f"\nFound {len(fast_queries)} query/warehouse combinations under 3 seconds:"
    )
    logger.info(fast_queries.to_string(index=False))
    logger.info("\n⚡ These queries are suitable for interactive/real-time use cases")

    # Example 5: Summary statistics for reporting
    logger.info("\n\n5. SUMMARY FOR EXECUTIVE REPORT")
    logger.info("-" * 80)
    summary = analyzer.conn.execute("""
        SELECT
            warehouse_size,
            COUNT(*) as total_runs,
            ROUND(AVG(execution_time_sec), 2) as avg_time,
            ROUND(SUM(execution_time_sec), 2) as total_time_sec,
            ROUND(SUM(execution_time_sec) / 3600, 3) as total_hours
        FROM benchmark_results
        WHERE run_type='warm'
        GROUP BY warehouse_size
        ORDER BY warehouse_size
    """).fetchdf()

    logger.info("\nPerformance & runtime summary (warm runs only):")
    logger.info(summary.to_string(index=False))

    # Calculate potential savings
    medium_total_time = summary[summary["warehouse_size"] == "MEDIUM"][
        "total_time_sec"
    ].values[0]
    xlarge_total_time = summary[summary["warehouse_size"] == "XLARGE"][
        "total_time_sec"
    ].values[0]
    time_saved = medium_total_time - xlarge_total_time
    pct_faster = (time_saved / medium_total_time) * 100

    logger.info("\n📊 Key Findings:")
    logger.info(f"   - XLARGE is {pct_faster:.1f}% faster than MEDIUM overall")
    logger.info(f"   - Time saved: {time_saved:.1f} seconds per test cycle")
    logger.info(
        f"   - For 100 daily query executions, XLARGE saves ~{(time_saved * 100 / 3600):.1f} hours/day"
    )

    # Close the analyzer
    analyzer.close()

    logger.info("\n" + "=" * 80)
    logger.info("Analysis complete! See ANALYSIS.md for more information.")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
