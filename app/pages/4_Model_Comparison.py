"""Model Comparison - Side-by-side solver evaluation and benchmarking."""

import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

src_path = Path(__file__).parent.parent.parent / "src"
app_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(app_path))

from ui_theme import apply_custom_css, render_hero

st.set_page_config(page_title="Model Comparison | RouteOpt", page_icon="📈", layout="wide")
apply_custom_css()

render_hero(
    title="📈 Multi-Algorithm Benchmarking & Comparison",
    subtitle="Audit solver trade-offs: total distance, vehicle utilization, runtime budgets, and optimality gaps.",
    badge="Step 4 • Evaluation Suite"
)

# Upload or Run Quick Benchmark
col_action1, col_action2 = st.columns([1, 2])

with col_action1:
    st.markdown("### 📥 Benchmark Ingestion")
    results_file = st.file_uploader("Load Results JSON", type=["json"], help="Upload benchmark_results.json")
    if results_file:
        try:
            results = json.load(results_file)
            st.session_state["benchmark_results"] = results
            st.success(f"Loaded {len(results)} algorithm runs!")
        except Exception as e:
            st.error(f"Error loading JSON: {e}")

    # Built-in sample benchmark loader if available
    sample_bench_path = Path("reports/benchmark_results.json")
    if sample_bench_path.exists():
        if st.button("📊 Load Cached Benchmark Results"):
            with open(sample_bench_path) as f:
                st.session_state["benchmark_results"] = json.load(f)
            st.success("Loaded cached benchmark runs!")

with col_action2:
    st.markdown("### 🎯 Benchmark CLI Command")
    st.markdown("""
    <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; padding: 16px;">
        <span style="color: #94A3B8; font-size: 0.85rem;">Run the automated test matrix directly from terminal:</span>
        <pre style="margin-top: 8px; color: #38BDF8; font-size: 0.9rem; font-family: monospace;">python -m routeopt.cli benchmark</pre>
        <span style="color: #64748B; font-size: 0.8rem;">Outputs are saved to <code>reports/benchmark_results.json</code> and <code>reports/benchmark_summary.csv</code>.</span>
    </div>
    """, unsafe_allow_html=True)

# Main Dashboard View
if "benchmark_results" in st.session_state:
    results = st.session_state["benchmark_results"]
    df = pd.DataFrame(results)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📊 Overall Matrix Performance")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Executions", len(df))
    with m2:
        st.metric("Evaluated Instances", df['instance_name'].nunique() if 'instance_name' in df.columns else 0)
    with m3:
        st.metric("Unique Algorithms", df['algorithm'].nunique() if 'algorithm' in df.columns else 0)
    with m4:
        feasible_rate = (df['feasible'].mean() * 100) if 'feasible' in df.columns else 0
        st.metric("Feasibility Rate", f"{feasible_rate:.1f}%")

    # Tabs for granular inspection
    tab_matrix, tab_instance, tab_rankings = st.tabs([
        "📋 Full Comparison Matrix", 
        "📈 Per-Instance Breakdown", 
        "🏆 Pareto & Algorithm Rankings"
    ])

    with tab_matrix:
        display_cols = [
            'instance_name', 'algorithm', 'total_distance', 'total_duration',
            'vehicles_used', 'capacity_utilization', 'feasible', 'gap_percent', 'runtime_seconds'
        ]
        available_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available_cols].sort_values(['instance_name', 'total_distance']), use_container_width=True)

    with tab_instance:
        if 'instance_name' in df.columns:
            instances = sorted(df['instance_name'].unique())
            selected_inst = st.selectbox("Select Benchmark Instance to Inspect", instances)
            sub_df = df[df['instance_name'] == selected_inst].sort_values('total_distance')

            c_chart1, c_chart2 = st.columns(2)
            with c_chart1:
                fig_dist = px.bar(
                    sub_df, x='algorithm', y='total_distance',
                    color='algorithm',
                    title=f"Total Distance by Solver: {selected_inst}",
                    template="plotly_dark"
                )
                fig_dist.update_layout(paper_bgcolor="rgba(15, 23, 42, 0.5)", plot_bgcolor="rgba(15, 23, 42, 0.5)", showlegend=False)
                st.plotly_chart(fig_dist, use_container_width=True)

            with c_chart2:
                fig_runtime = px.bar(
                    sub_df, x='algorithm', y='runtime_seconds',
                    color='algorithm',
                    title=f"Runtime (seconds): {selected_inst}",
                    template="plotly_dark"
                )
                fig_runtime.update_layout(paper_bgcolor="rgba(15, 23, 42, 0.5)", plot_bgcolor="rgba(15, 23, 42, 0.5)", showlegend=False)
                st.plotly_chart(fig_runtime, use_container_width=True)

    with tab_rankings:
        feasible_df = df[df['feasible'] == True] if 'feasible' in df.columns else df
        if len(feasible_df) > 0 and 'total_distance' in feasible_df.columns:
            agg_df = feasible_df.groupby('algorithm').agg({
                'total_distance': 'mean',
                'vehicles_used': 'mean',
                'runtime_seconds': 'mean',
            }).round(2).reset_index()

            st.markdown("#### Mean Performance Across All Test Scenarios")
            st.dataframe(agg_df, use_container_width=True)

            fig_scatter = px.scatter(
                agg_df, x='runtime_seconds', y='total_distance',
                size='vehicles_used', text='algorithm',
                title="Pareto Trade-off: Runtime vs Total Solution Distance",
                labels={'runtime_seconds': 'Runtime (s)', 'total_distance': 'Mean Distance'},
                template="plotly_dark"
            )
            fig_scatter.update_traces(textposition='top center')
            fig_scatter.update_layout(paper_bgcolor="rgba(15, 23, 42, 0.5)", plot_bgcolor="rgba(15, 23, 42, 0.5)")
            st.plotly_chart(fig_scatter, use_container_width=True)
else:
    st.markdown("""
    <div class="glass-card" style="text-align: center; padding: 40px; margin-top: 20px;">
        <h4 style="color: #94A3B8; margin-bottom: 8px;">No Benchmark Run Data Loaded</h4>
        <p style="color: #64748B; font-size: 0.95rem;">
            Run <code>python -m routeopt.cli benchmark</code> from terminal or upload an existing <code>benchmark_results.json</code> to view comparison diagnostics.
        </p>
    </div>
    """, unsafe_allow_html=True)
