#!/usr/bin/env python3
"""
Analyze benchmark results using DuckDB.

This script provides various analyses of the benchmark results including:
- Summary statistics by warehouse size and query
- Cold vs warm run comparisons
- Performance metrics across different run types
- Query performance rankings
"""

import duckdb
import logging
import pandas as pd
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BenchmarkAnalyzer:
    """Analyze benchmark results using DuckDB."""

    def __init__(self, results_path: str):
        """Initialize the analyzer with the path to benchmark results CSV."""
        self.results_path = Path(results_path)
        if not self.results_path.exists():
            raise FileNotFoundError(f"Results file not found: {results_path}")

        self.conn = duckdb.connect(":memory:")
        self._load_data()

    def _load_data(self):
        """Load benchmark results into DuckDB."""
        logger.info(f"Loading data from {self.results_path}")

        # Load CSV using pandas first (more forgiving with complex fields)
        df = pd.read_csv(self.results_path)

        # Register the dataframe as a DuckDB table
        self.conn.execute("CREATE TABLE benchmark_results AS SELECT * FROM df")

        # Get basic stats
        count = self.conn.execute("SELECT COUNT(*) FROM benchmark_results").fetchone()[
            0
        ]
        logger.info(f"Loaded {count} benchmark records")

    def summary_stats(self) -> None:
        """Display summary statistics of the benchmark results."""
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY STATISTICS")
        logger.info("=" * 80)

        result = self.conn.execute("""
            SELECT
                COUNT(*) as total_runs,
                COUNT(DISTINCT run_id) as unique_run_ids,
                COUNT(DISTINCT query_num) as unique_queries,
                COUNT(DISTINCT warehouse_size) as warehouse_sizes,
                MIN(execution_time_sec) as min_exec_time,
                MAX(execution_time_sec) as max_exec_time,
                AVG(execution_time_sec) as avg_exec_time,
                MEDIAN(execution_time_sec) as median_exec_time
            FROM benchmark_results
        """).fetchdf()

        logger.info("\n" + result.to_string(index=False))

    def warehouse_comparison(self) -> None:
        """Compare performance across warehouse sizes."""
        logger.info("\n" + "=" * 80)
        logger.info("PERFORMANCE BY WAREHOUSE SIZE")
        logger.info("=" * 80)

        result = self.conn.execute("""
            SELECT
                warehouse_size,
                COUNT(*) as total_runs,
                ROUND(AVG(execution_time_sec), 3) as avg_exec_time,
                ROUND(MEDIAN(execution_time_sec), 3) as median_exec_time,
                ROUND(MIN(execution_time_sec), 3) as min_exec_time,
                ROUND(MAX(execution_time_sec), 3) as max_exec_time,
                ROUND(STDDEV(execution_time_sec), 3) as stddev_exec_time
            FROM benchmark_results
            GROUP BY warehouse_size
            ORDER BY
                CASE warehouse_size
                    WHEN 'SMALL' THEN 1
                    WHEN 'MEDIUM' THEN 2
                    WHEN 'XLARGE' THEN 3
                    ELSE 4
                END
        """).fetchdf()

        logger.info("\n" + result.to_string(index=False))

    def run_type_comparison(self) -> None:
        """Compare cold vs warm vs semi-warm run performance."""
        logger.info("\n" + "=" * 80)
        logger.info("PERFORMANCE BY RUN TYPE (Cold vs Warm vs Semi-warm)")
        logger.info("=" * 80)

        result = self.conn.execute("""
            SELECT
                run_type,
                COUNT(*) as total_runs,
                ROUND(AVG(execution_time_sec), 3) as avg_exec_time,
                ROUND(MEDIAN(execution_time_sec), 3) as median_exec_time,
                ROUND(MIN(execution_time_sec), 3) as min_exec_time,
                ROUND(MAX(execution_time_sec), 3) as max_exec_time
            FROM benchmark_results
            GROUP BY run_type
            ORDER BY
                CASE run_type
                    WHEN 'cold' THEN 1
                    WHEN 'semi-warm' THEN 2
                    WHEN 'warm' THEN 3
                    ELSE 4
                END
        """).fetchdf()

        logger.info("\n" + result.to_string(index=False))

    def query_performance_ranking(self, limit: int = 10) -> None:
        """Show fastest and slowest queries."""
        logger.info("\n" + "=" * 80)
        logger.info(f"TOP {limit} FASTEST QUERIES (by average execution time)")
        logger.info("=" * 80)

        result = self.conn.execute(f"""
            SELECT
                query_num,
                COUNT(*) as run_count,
                ROUND(AVG(execution_time_sec), 3) as avg_exec_time,
                ROUND(MEDIAN(execution_time_sec), 3) as median_exec_time,
                ROUND(MIN(execution_time_sec), 3) as min_exec_time,
                ROUND(MAX(execution_time_sec), 3) as max_exec_time
            FROM benchmark_results
            GROUP BY query_num
            ORDER BY avg_exec_time ASC
            LIMIT {limit}
        """).fetchdf()

        logger.info("\n" + result.to_string(index=False))

        logger.info("\n" + "=" * 80)
        logger.info(f"TOP {limit} SLOWEST QUERIES (by average execution time)")
        logger.info("=" * 80)

        result = self.conn.execute(f"""
            SELECT
                query_num,
                COUNT(*) as run_count,
                ROUND(AVG(execution_time_sec), 3) as avg_exec_time,
                ROUND(MEDIAN(execution_time_sec), 3) as median_exec_time,
                ROUND(MIN(execution_time_sec), 3) as min_exec_time,
                ROUND(MAX(execution_time_sec), 3) as max_exec_time
            FROM benchmark_results
            GROUP BY query_num
            ORDER BY avg_exec_time DESC
            LIMIT {limit}
        """).fetchdf()

        logger.info("\n" + result.to_string(index=False))

    def warehouse_query_matrix(self) -> None:
        """Show average execution time matrix: warehouse size x query number."""
        logger.info("\n" + "=" * 80)
        logger.info("QUERY PERFORMANCE MATRIX (Average Execution Time in seconds)")
        logger.info("=" * 80)

        result = self.conn.execute("""
            SELECT
                query_num,
                ROUND(AVG(CASE WHEN warehouse_size = 'SMALL' THEN execution_time_sec END), 3) as small,
                ROUND(AVG(CASE WHEN warehouse_size = 'MEDIUM' THEN execution_time_sec END), 3) as medium,
                ROUND(AVG(CASE WHEN warehouse_size = 'XLARGE' THEN execution_time_sec END), 3) as xlarge
            FROM benchmark_results
            GROUP BY query_num
            ORDER BY query_num
        """).fetchdf()

        logger.info("\n" + result.to_string(index=False))

    def warm_vs_cold_speedup(self) -> None:
        """Calculate speedup from cold to warm runs."""
        logger.info("\n" + "=" * 80)
        logger.info("COLD TO WARM SPEEDUP ANALYSIS")
        logger.info("=" * 80)

        result = self.conn.execute("""
            WITH cold_times AS (
                SELECT
                    warehouse_size,
                    query_num,
                    AVG(execution_time_sec) as cold_avg
                FROM benchmark_results
                WHERE run_type = 'cold'
                GROUP BY warehouse_size, query_num
            ),
            warm_times AS (
                SELECT
                    warehouse_size,
                    query_num,
                    AVG(execution_time_sec) as warm_avg
                FROM benchmark_results
                WHERE run_type = 'warm'
                GROUP BY warehouse_size, query_num
            )
            SELECT
                c.warehouse_size,
                COUNT(*) as queries_compared,
                ROUND(AVG(c.cold_avg), 3) as avg_cold_time,
                ROUND(AVG(w.warm_avg), 3) as avg_warm_time,
                ROUND(AVG(c.cold_avg - w.warm_avg), 3) as avg_time_saved,
                ROUND(AVG((c.cold_avg - w.warm_avg) / c.cold_avg * 100), 1) as avg_speedup_pct
            FROM cold_times c
            JOIN warm_times w
                ON c.warehouse_size = w.warehouse_size
                AND c.query_num = w.query_num
            GROUP BY c.warehouse_size
            ORDER BY
                CASE c.warehouse_size
                    WHEN 'SMALL' THEN 1
                    WHEN 'MEDIUM' THEN 2
                    WHEN 'XLARGE' THEN 3
                    ELSE 4
                END
        """).fetchdf()

        logger.info("\n" + result.to_string(index=False))

    def detailed_query_analysis(self, query_num: int) -> None:
        """Detailed analysis for a specific query number."""
        logger.info("\n" + "=" * 80)
        logger.info(f"DETAILED ANALYSIS FOR QUERY {query_num}")
        logger.info("=" * 80)

        result = self.conn.execute(f"""
            SELECT
                warehouse_size,
                run_type,
                run_num,
                ROUND(execution_time_sec, 3) as exec_time_sec,
                rows_produced,
                query_id
            FROM benchmark_results
            WHERE query_num = {query_num}
            ORDER BY warehouse_size, run_type, run_num
        """).fetchdf()

        logger.info("\n" + result.to_string(index=False))

    def export_summary_to_csv(self, output_path: str = "analysis_summary.csv") -> None:
        """Export summary statistics to CSV."""
        logger.info(f"\nExporting summary to {output_path}")

        result = self.conn.execute("""
            SELECT
                warehouse_size,
                query_num,
                run_type,
                COUNT(*) as run_count,
                ROUND(AVG(execution_time_sec), 3) as avg_exec_time,
                ROUND(MEDIAN(execution_time_sec), 3) as median_exec_time,
                ROUND(MIN(execution_time_sec), 3) as min_exec_time,
                ROUND(MAX(execution_time_sec), 3) as max_exec_time,
                ROUND(STDDEV(execution_time_sec), 3) as stddev_exec_time
            FROM benchmark_results
            GROUP BY warehouse_size, query_num, run_type
            ORDER BY warehouse_size, query_num, run_type
        """).fetchdf()

        result.to_csv(output_path, index=False)
        logger.info(f"Summary exported to {output_path}")

    def custom_query(self, sql: str) -> None:
        """Execute a custom SQL query against the benchmark data."""
        logger.info("\n" + "=" * 80)
        logger.info("CUSTOM QUERY RESULTS")
        logger.info("=" * 80)
        logger.info(f"\nSQL: {sql}\n")

        try:
            result = self.conn.execute(sql).fetchdf()
            logger.info("\n" + result.to_string(index=False))
        except Exception as e:
            logger.error(f"Error executing query: {e}")

    def close(self):
        """Close the DuckDB connection."""
        self.conn.close()


def main():
    """Main entry point for the analysis script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze Snowflake benchmark results using DuckDB"
    )
    parser.add_argument(
        "--results",
        default="../results/benchmark_results.csv",
        help="Path to benchmark results CSV file",
    )
    parser.add_argument(
        "--query", type=int, help="Show detailed analysis for specific query number"
    )
    parser.add_argument(
        "--export", metavar="OUTPUT_FILE", help="Export summary statistics to CSV file"
    )
    parser.add_argument("--sql", help="Execute custom SQL query against benchmark data")
    parser.add_argument("--all", action="store_true", help="Run all standard analyses")

    args = parser.parse_args()

    try:
        analyzer = BenchmarkAnalyzer(args.results)

        if args.sql:
            analyzer.custom_query(args.sql)
        elif args.query:
            analyzer.detailed_query_analysis(args.query)
        elif args.export:
            analyzer.export_summary_to_csv(args.export)
        elif args.all:
            analyzer.summary_stats()
            analyzer.warehouse_comparison()
            analyzer.run_type_comparison()
            analyzer.query_performance_ranking()
            analyzer.warehouse_query_matrix()
            analyzer.warm_vs_cold_speedup()
        else:
            # Default: show key analyses
            analyzer.summary_stats()
            analyzer.warehouse_comparison()
            analyzer.run_type_comparison()
            analyzer.query_performance_ranking(limit=5)

        analyzer.close()

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


if __name__ == "__main__":
    main()
