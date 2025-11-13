#!/usr/bin/env python3
"""
Streamlit dashboard for Snowflake benchmark analysis.

Usage:
    cd snowflake/analysis
    uv run streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import duckdb

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_DATA_PATH = SCRIPT_DIR / ".." / "results" / "benchmark_results.csv"

# Page config
st.set_page_config(
    page_title="Snowflake Benchmark Dashboard", page_icon="❄️", layout="wide"
)

# Custom CSS
st.markdown(
    """
    <style>
    .main > div {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .stMetric label {
        color: #31333F !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #0e1117 !important;
    }
    .stMetric [data-testid="stMetricDelta"] {
        color: #31333F !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_data(file_path: str = None):
    """Load and cache the benchmark data."""
    if file_path is None:
        file_path = str(DEFAULT_DATA_PATH)
    df = pd.read_csv(file_path)
    return df


@st.cache_data
def get_summary_stats(df):
    """Calculate summary statistics."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE results AS SELECT * FROM df")

    stats = conn.execute("""
        SELECT
            COUNT(*) as total_runs,
            COUNT(DISTINCT query_num) as unique_queries,
            ROUND(AVG(execution_time_sec), 2) as avg_exec_time,
            ROUND(MIN(execution_time_sec), 2) as min_exec_time,
            ROUND(MAX(execution_time_sec), 2) as max_exec_time
        FROM results
    """).fetchdf()

    conn.close()
    return stats.iloc[0]


def main():
    st.title("❄️ Snowflake Benchmark Dashboard")
    st.markdown("Analysis of TPC-H query performance across warehouse sizes")

    # Load data
    try:
        df = load_data()
    except FileNotFoundError:
        st.error("❌ Benchmark results file not found. Please run benchmarks first.")
        st.info(f"Expected location: `{DEFAULT_DATA_PATH}`")
        return

    # Filter options in sidebar
    st.sidebar.header("Filters")

    # Run ID filter (primary filter - applies to entire dataset)
    st.sidebar.subheader("🎯 Benchmark Run")
    unique_runs = df["run_id"].unique()

    # Get run info with timestamps
    run_info = (
        df.groupby("run_id")
        .agg({"timestamp": "min", "run_id": "first"})
        .sort_values("timestamp", ascending=False)
    )

    # Create display options with timestamp
    run_options = ["All Runs"] + [
        f"{row['run_id'][:8]}... ({pd.to_datetime(row['timestamp']).strftime('%Y-%m-%d %H:%M')})"
        for _, row in run_info.iterrows()
    ]
    run_ids_list = ["All"] + run_info["run_id"].tolist()

    selected_run_display = st.sidebar.selectbox(
        "Select Benchmark Run",
        run_options,
        help="Choose a specific benchmark run or view all runs combined",
    )

    # Get the actual run_id from selection
    selected_run_idx = run_options.index(selected_run_display)
    selected_run_id = run_ids_list[selected_run_idx]

    # Apply run_id filter first
    if selected_run_id != "All":
        df = df[df["run_id"] == selected_run_id].copy()
        st.sidebar.success(f"Analyzing run: {selected_run_id[:16]}...")
    else:
        st.sidebar.info(f"Analyzing {len(unique_runs)} run(s)")

    st.sidebar.divider()

    # Secondary filters
    st.sidebar.subheader("📊 Data Filters")

    # Warehouse size filter
    warehouse_sizes = ["All"] + sorted(df["warehouse_size"].unique().tolist())
    selected_warehouse = st.sidebar.selectbox("Warehouse Size", warehouse_sizes)

    # Run type filter
    run_types = ["All"] + sorted(df["run_type"].unique().tolist())
    selected_run_type = st.sidebar.selectbox("Run Type", run_types)

    # Apply additional filters
    filtered_df = df.copy()
    if selected_warehouse != "All":
        filtered_df = filtered_df[filtered_df["warehouse_size"] == selected_warehouse]
    if selected_run_type != "All":
        filtered_df = filtered_df[filtered_df["run_type"] == selected_run_type]

    st.divider()

    # Summary metrics at top
    st.header("📊 Overview")
    stats = get_summary_stats(filtered_df)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Runs", f"{int(stats['total_runs']):,}")
    with col2:
        st.metric("Unique Queries", f"{int(stats['unique_queries'])}")
    with col3:
        st.metric("Avg Exec Time", f"{stats['avg_exec_time']}s")
    with col4:
        st.metric("Min Time", f"{stats['min_exec_time']}s")
    with col5:
        st.metric("Max Time", f"{stats['max_exec_time']}s")

    # Main visualizations

    # 1. Warehouse Size Performance Comparison
    st.header("1️⃣ Performance by Warehouse Size")

    warehouse_stats = (
        filtered_df.groupby("warehouse_size")
        .agg({"execution_time_sec": ["mean", "median", "std", "min", "max"]})
        .round(3)
    )
    warehouse_stats.columns = ["Mean", "Median", "Std Dev", "Min", "Max"]
    warehouse_stats = warehouse_stats.reset_index()

    # Sort by warehouse size
    size_order = {"SMALL": 1, "MEDIUM": 2, "LARGE": 3, "XLARGE": 4, "XXLARGE": 5}
    warehouse_stats["sort_order"] = warehouse_stats["warehouse_size"].map(
        lambda x: size_order.get(x, 99)
    )
    warehouse_stats = warehouse_stats.sort_values("sort_order").drop(
        "sort_order", axis=1
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=warehouse_stats["warehouse_size"],
                y=warehouse_stats["Mean"],
                name="Mean",
                marker_color="#1f77b4",
            )
        )
        fig.add_trace(
            go.Bar(
                x=warehouse_stats["warehouse_size"],
                y=warehouse_stats["Median"],
                name="Median",
                marker_color="#ff7f0e",
            )
        )
        fig.update_layout(
            title="Average Execution Time by Warehouse Size",
            xaxis_title="Warehouse Size",
            yaxis_title="Execution Time (seconds)",
            barmode="group",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.dataframe(warehouse_stats, use_container_width=True, hide_index=True)

    st.divider()

    # 2. Query Performance Crosstab
    st.header("2️⃣ Query Performance by Run Type and Warehouse Size")
    st.markdown(
        "Execution times (seconds) for each query and run type across warehouse sizes. Note: cold and semi-warm runs are combined."
    )

    # Combine cold and semi-warm into a single category
    crosstab_df = filtered_df.copy()
    crosstab_df["run_type_grouped"] = crosstab_df["run_type"].replace(
        {"semi-warm": "cold"}
    )

    # Create crosstab with query_num on rows and multi-index (warehouse_size, run_type) on columns
    crosstab_data = (
        crosstab_df.groupby(["query_num", "warehouse_size", "run_type_grouped"])[
            "execution_time_sec"
        ]
        .mean()
        .reset_index()
    )
    crosstab_pivot = crosstab_data.pivot_table(
        index="query_num",
        columns=["warehouse_size", "run_type_grouped"],
        values="execution_time_sec",
        aggfunc="mean",
    )

    # Reorder columns by warehouse size
    available_sizes = [
        s
        for s in ["SMALL", "MEDIUM", "LARGE", "XLARGE", "XXLARGE"]
        if s in crosstab_pivot.columns.get_level_values(0).unique()
    ]
    # Reorder to get warehouse sizes in order with all run types under each
    crosstab_pivot = crosstab_pivot.reindex(columns=available_sizes, level=0)

    # Remove rows that are all NaN
    crosstab_pivot = crosstab_pivot.dropna(how="all")

    # Round values for display
    crosstab_pivot = crosstab_pivot.round(3)

    # Apply styling with background gradient bars
    styled_crosstab = crosstab_pivot.style.background_gradient(
        cmap="RdYlGn_r",
        axis=None,
        vmin=crosstab_pivot.min().min(),
        vmax=crosstab_pivot.max().max(),
    ).format("{:.3f}", na_rep="-")

    # Display the crosstab
    st.dataframe(
        styled_crosstab,
        use_container_width=True,
        height=min(600, len(crosstab_pivot) * 35 + 100),
    )

    st.divider()

    # 3. Cold vs Warm Performance
    st.header("3️⃣ Cold vs Warm Performance")
    st.markdown(
        "Comparing first run (cold) vs subsequent runs (warm) to measure caching benefits"
    )

    # Filter for cold and warm runs only
    cold_warm_df = filtered_df[filtered_df["run_type"].isin(["cold", "warm"])]

    if len(cold_warm_df) > 0:
        run_type_stats = (
            cold_warm_df.groupby(["warehouse_size", "run_type"])["execution_time_sec"]
            .mean()
            .reset_index()
        )

        # Create grouped bar chart
        fig = px.bar(
            run_type_stats,
            x="warehouse_size",
            y="execution_time_sec",
            color="run_type",
            barmode="group",
            color_discrete_map={"cold": "#1f77b4", "warm": "#ff7f0e"},
            labels={
                "execution_time_sec": "Avg Execution Time (s)",
                "warehouse_size": "Warehouse Size",
            },
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

        # Calculate speedup
        st.subheader("💨 Warm Run Speedup")
        speedup_data = []
        for warehouse in cold_warm_df["warehouse_size"].unique():
            cold_time = cold_warm_df[
                (cold_warm_df["warehouse_size"] == warehouse)
                & (cold_warm_df["run_type"] == "cold")
            ]["execution_time_sec"].mean()

            warm_time = cold_warm_df[
                (cold_warm_df["warehouse_size"] == warehouse)
                & (cold_warm_df["run_type"] == "warm")
            ]["execution_time_sec"].mean()

            if pd.notna(cold_time) and pd.notna(warm_time) and cold_time > 0:
                speedup_pct = ((cold_time - warm_time) / cold_time) * 100
                speedup_data.append(
                    {
                        "Warehouse": warehouse,
                        "Cold Avg (s)": round(cold_time, 3),
                        "Warm Avg (s)": round(warm_time, 3),
                        "Time Saved (s)": round(cold_time - warm_time, 3),
                        "Speedup (%)": round(speedup_pct, 1),
                    }
                )

        if speedup_data:
            speedup_df = pd.DataFrame(speedup_data)
            # Sort by warehouse size
            speedup_df["sort_order"] = speedup_df["Warehouse"].map(
                lambda x: size_order.get(x, 99)
            )
            speedup_df = speedup_df.sort_values("sort_order").drop("sort_order", axis=1)
            st.dataframe(speedup_df, use_container_width=True, hide_index=True)
    else:
        st.info("No cold/warm run comparison data available with current filters.")

    # Footer
    st.divider()
    st.markdown(
        """
        <div style='text-align: center; color: #666; padding: 1rem;'>
            <small>Data source: benchmark_results.csv |
            Built with Streamlit |
            For detailed analysis, see <a href='ANALYSIS.md'>ANALYSIS.md</a></small>
        </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
