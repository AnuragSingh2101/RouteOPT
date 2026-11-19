"""RouteOpt - Last-Mile Delivery Route Optimization Dashboard."""

import streamlit as st
from pathlib import Path
import sys

# Add src and app to path
src_path = Path(__file__).parent.parent / "src"
app_path = Path(__file__).parent
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(app_path))

from ui_theme import apply_custom_css, render_hero

st.set_page_config(
    page_title="RouteOpt | Last-Mile Delivery Optimization",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_css()


def main():
    render_hero(
        title="🚚 RouteOpt System",
        subtitle="Enterprise-grade last-mile delivery route optimization, fleet planning, and combinatorial search engine.",
        badge="Autonomous Routing Platform"
    )

    # Sidebar navigation
    with st.sidebar:
        st.markdown("### 🧭 RouteOpt Console")
        st.markdown("""
        **Core Solver Engines:**
        - **CVRP**: Capacitated Vehicle Routing
        - **VRPTW**: Routing with Time Windows
        - **Fleet Optimization**: Sizing & Balance
        
        **Available Solvers:**
        - ⚡ *Nearest Neighbor* (Fast Greedy)
        - 📐 *Clarke-Wright Savings*
        - 🔄 *Local Search* (2-Opt / Swap / Relocate)
        - 🎯 *Google OR-Tools* (Constraint & Metaheuristics)
        - 🔬 *Exact MILP* (MTZ via HiGHS/SciPy)
        """)
        st.markdown("---")
        st.caption("RouteOpt v0.1.0 • Built for High Performance")

    # Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Active Engines", value="5 Solvers", delta="Heuristics + Exact")
    with col2:
        st.metric(label="Constraint Modes", value="CVRP / VRPTW", delta="Capacitated & TW")
    with col3:
        st.metric(label="Distance Metrics", value="3 Supported", delta="Euclidean / Haversine / OSRM")
    with col4:
        st.metric(label="Validator", value="Independent", delta="100% Strict Audit")

    st.markdown("<br>", unsafe_allow_html=True)

    # Feature Cards
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div class="glass-card">
            <div class="card-header">📊 1. Data Ingestion & Validation</div>
            <p style="color: #94A3B8; font-size: 0.95rem; line-height: 1.6;">
                Upload custom customer delivery orders via CSV or choose from gold-standard 
                <strong>CVRPLIB</strong> (Augerat, Uchoa) and <strong>Solomon VRPTW</strong> benchmark datasets. 
                Full automated verification of demand, capacity, time windows, and coordinates.
            </p>
            <span class="status-pill pill-success">CSV & Benchmark Ready</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="glass-card">
            <div class="card-header">⚙️ 2. Combinatorial Optimization</div>
            <p style="color: #94A3B8; font-size: 0.95rem; line-height: 1.6;">
                Execute state-of-the-art metaheuristics: <em>Guided Local Search</em>, <em>Tabu Search</em>, 
                and <em>Simulated Annealing</em> alongside exact Mixed Integer Linear Programming (MILP). 
                Customize multi-objective priorities, search budgets, and fleet constraints.
            </p>
            <span class="status-pill pill-info">OR-Tools + HiGHS</span>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="glass-card">
            <div class="card-header">🗺️ 3. Interactive Route Cartography</div>
            <p style="color: #94A3B8; font-size: 0.95rem; line-height: 1.6;">
                Inspect interactive stop-by-stop route maps rendered with Plotly. 
                Visual indicators for vehicle dispatch, customer sequence ordering, delivery loads, 
                and arrival timeline schedules for both planar coordinate systems and real GPS coordinates.
            </p>
            <span class="status-pill pill-info">Plotly Geographic Engine</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="glass-card">
            <div class="card-header">🔬 4. Sensitivity & Benchmarking</div>
            <p style="color: #94A3B8; font-size: 0.95rem; line-height: 1.6;">
                Run multi-seed Monte Carlo sensitivity sweeps across customer density, fleet limits, 
                and window tighteness. Conduct side-by-side Pareto optimality comparisons with Wilcoxon 
                and paired t-test statistical validation.
            </p>
            <span class="status-pill pill-warning">Statistical Validation</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Quick Workflow Guide
    st.markdown("""
    <div class="glass-card">
        <div class="card-header">🚀 Quick Navigation Guide</div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-top: 12px;">
            <div style="background: rgba(15, 23, 42, 0.6); padding: 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.05);">
                <div style="font-weight: 700; color: #38BDF8; margin-bottom: 4px;">Step 1: Ingest Data</div>
                <div style="font-size: 0.85rem; color: #94A3B8;">Go to <strong>Delivery Data</strong>, upload your CSV or pick sample data, configure fleet capacity.</div>
            </div>
            <div style="background: rgba(15, 23, 42, 0.6); padding: 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.05);">
                <div style="font-weight: 700; color: #60A5FA; margin-bottom: 4px;">Step 2: Optimize</div>
                <div style="font-size: 0.85rem; color: #94A3B8;">Navigate to <strong>Route Optimization</strong>, pick your algorithm, tune timeout, click Run.</div>
            </div>
            <div style="background: rgba(15, 23, 42, 0.6); padding: 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.05);">
                <div style="font-weight: 700; color: #818CF8; margin-bottom: 4px;">Step 3: Map & Dispatch</div>
                <div style="font-size: 0.85rem; color: #94A3B8;">Open <strong>Route Map</strong> to trace route geometry, stops sequence, and vehicle loads.</div>
            </div>
            <div style="background: rgba(15, 23, 42, 0.6); padding: 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.05);">
                <div style="font-weight: 700; color: #A78BFA; margin-bottom: 4px;">Step 4: Analyze</div>
                <div style="font-size: 0.85rem; color: #94A3B8;">Visit <strong>Model Comparison</strong> & <strong>Scenario Analysis</strong> for deep performance audits.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
