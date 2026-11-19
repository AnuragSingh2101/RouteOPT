"""Route Optimization - Modern Algorithm Execution & Diagnostic Console."""

import streamlit as st
import pandas as pd
import numpy as np
import time
from pathlib import Path
import sys
import json

src_path = Path(__file__).parent.parent.parent / "src"
app_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(app_path))

from routeopt.algorithms import nearest_neighbor, clarke_wright_savings, solve_with_local_search
from routeopt.optimization import (
    solve_cvrp_ortools, solve_vrptw_ortools,
    solve_cvrp_exact_mtz,
    ORToolsSolverConfig,
)
from routeopt.evaluation import validate_solution, compute_metrics
from ui_theme import apply_custom_css, render_hero

st.set_page_config(page_title="Optimization | RouteOpt", page_icon="⚙️", layout="wide")
apply_custom_css()

render_hero(
    title="⚙️ Combinatorial Route Optimization",
    subtitle="Configure metaheuristic hyperparameters, search budgets, and solve capacitated routing instances.",
    badge="Step 2 • Solver Engine"
)

# Guard: check for instance
if "current_instance" not in st.session_state:
    st.markdown("""
    <div class="glass-card" style="text-align: center; padding: 40px;">
        <h3 style="color: #F87171; margin-bottom: 8px;">⚠️ No Instance Active</h3>
        <p style="color: #94A3B8; font-size: 1rem; max-width: 500px; margin: 0 auto 20px auto;">
            Please visit the <strong>Delivery Data</strong> page first to upload your CSV, select a benchmark, or load a sample dataset.
        </p>
        <a href="Delivery_Data" target="_self" style="text-decoration: none;">
            <span class="status-pill pill-info" style="font-size: 0.95rem; padding: 8px 18px;">👉 Go to Delivery Data</span>
        </a>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

instance = st.session_state["current_instance"]
dist_matrix = instance.distance_matrix
time_matrix = instance.time_matrix if instance.has_time_windows else None

# Active Instance Banner
st.markdown(f"""
<div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px 20px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
    <div>
        <span style="color: #64748B; font-size: 0.85rem; text-transform: uppercase; font-weight: 600;">Active Model</span>
        <div style="color: #F1F5F9; font-size: 1.15rem; font-weight: 700;">{instance.metadata.name}</div>
    </div>
    <div style="display: flex; gap: 20px;">
        <div>
            <span style="color: #64748B; font-size: 0.8rem;">Customers</span>
            <div style="color: #38BDF8; font-weight: 700;">{instance.num_customers}</div>
        </div>
        <div>
            <span style="color: #64748B; font-size: 0.8rem;">Available Fleet</span>
            <div style="color: #818CF8; font-weight: 700;">{len(instance.vehicles)}</div>
        </div>
        <div>
            <span style="color: #64748B; font-size: 0.8rem;">Vehicle Cap</span>
            <div style="color: #A78BFA; font-weight: 700;">{instance.vehicles[0].capacity:.0f}</div>
        </div>
        <div>
            <span style="color: #64748B; font-size: 0.8rem;">Time Windows</span>
            <div style="color: {'#4ADE80' if instance.has_time_windows else '#94A3B8'}; font-weight: 700;">
                {'Enabled' if instance.has_time_windows else 'Disabled'}
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Solver Settings in 2 Columns
cfg_col1, cfg_col2 = st.columns([1, 1])

with cfg_col1:
    st.markdown("### 1. Algorithm Selection")
    algo_options = [
        "Google OR-Tools (State-of-the-art Metaheuristics)",
        "Clarke-Wright Savings (Classic Construction)",
        "Savings + Local Search (2-Opt & Relocate)",
        "Nearest Neighbor (Greedy Baseline)",
        "Exact MILP (HiGHS / SciPy - Tiny Instances ≤12)",
    ]
    if instance.has_time_windows:
        algo_options.insert(1, "Google OR-Tools VRPTW (Time Windows Dedicated)")

    chosen_algo_label = st.selectbox("Select Optimization Method", algo_options)

with cfg_col2:
    st.markdown("### 2. Search Hyperparameters")
    
    if "OR-Tools" in chosen_algo_label:
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            time_limit = st.slider("Search Budget (seconds)", min_value=2, max_value=120, value=15)
            first_strategy = st.selectbox(
                "First Solution Strategy",
                ["PATH_CHEAPEST_ARC", "SAVINGS", "PARALLEL_CHEAPEST_INSERTION", "CHRISTOFIDES"]
            )
        with p_col2:
            metaheuristic = st.selectbox(
                "Metaheuristic Operator",
                ["GUIDED_LOCAL_SEARCH", "TABU_SEARCH", "SIMULATED_ANNEALING"]
            )
            scale_factor = st.number_input("Cost Scaling Factor", value=100 if instance.metadata.source == "Solomon" else 1, min_value=1)
        
        lexicographic = st.checkbox("Lexicographic vehicle minimization (reduce active trucks first)", value=True)
    
    elif "Exact MILP" in chosen_algo_label:
        time_limit = st.slider("MILP Solver Timeout (s)", min_value=5, max_value=180, value=30)
        solver_backend = st.radio("MILP Backend", ["scipy", "pulp"], horizontal=True)
        if instance.num_customers > 12:
            st.error(f"⚠️ Exact MTZ formulation scales factorially. Instance has {instance.num_customers} stops (limit: ≤12).")
            
    else:
        consider_tw = st.checkbox(
            "Respect Time Windows",
            value=instance.has_time_windows,
            disabled=not instance.has_time_windows
        )
        st.info("Heuristic solvers run near-instantaneously without timeout budgets.")

st.markdown("<br>", unsafe_allow_html=True)

# Run Button
if st.button("🚀 Execute Optimization Run", type="primary", use_container_width=True):
    if "Exact MILP" in chosen_algo_label and instance.num_customers > 12:
        st.error("Cannot run exact MILP for instances exceeding 12 customers.")
        st.stop()
        
    with st.spinner(f"Computing optimal routes via {chosen_algo_label}..."):
        t0 = time.time()
        solution = None
        
        try:
            if chosen_algo_label == "Nearest Neighbor (Greedy Baseline)":
                solution = nearest_neighbor(instance, dist_matrix, time_matrix, consider_time_windows=consider_tw)
                
            elif chosen_algo_label == "Clarke-Wright Savings (Classic Construction)":
                solution = clarke_wright_savings(instance, dist_matrix, time_matrix, consider_time_windows=consider_tw)
                
            elif chosen_algo_label == "Savings + Local Search (2-Opt & Relocate)":
                solution = solve_with_local_search(instance, dist_matrix, time_matrix, consider_time_windows=consider_tw)
                
            elif "VRPTW" in chosen_algo_label:
                config = ORToolsSolverConfig(
                    time_limit_seconds=time_limit,
                    scale_factor=scale_factor,
                    first_solution_strategy=first_strategy,
                    local_search_metaheuristic=metaheuristic,
                    consider_time_windows=True,
                    use_fixed_vehicle_cost=lexicographic,
                )
                solution = solve_vrptw_ortools(instance, dist_matrix, time_matrix, config=config)
                
            elif "OR-Tools" in chosen_algo_label:
                config = ORToolsSolverConfig(
                    time_limit_seconds=time_limit,
                    scale_factor=scale_factor,
                    first_solution_strategy=first_strategy,
                    local_search_metaheuristic=metaheuristic,
                    use_fixed_vehicle_cost=lexicographic,
                )
                solution = solve_cvrp_ortools(instance, dist_matrix, config=config)
                
            elif "Exact MILP" in chosen_algo_label:
                solution = solve_cvrp_exact_mtz(instance, dist_matrix, time_limit_seconds=time_limit, solver=solver_backend)

            elapsed = time.time() - t0
            solution.runtime_seconds = elapsed
            
            # Independent Validation
            val_result = validate_solution(solution, instance, dist_matrix, time_matrix)
            metrics = compute_metrics(solution, instance, dist_matrix, time_matrix)
            
            st.session_state["last_solution"] = solution
            st.session_state["last_validation"] = val_result
            st.session_state["last_metrics"] = metrics
            
            st.success(f"Optimization finished in {elapsed:.2f} seconds!")
            
        except Exception as e:
            st.error(f"Solver Error: {e}")
            st.exception(e)

# Display Results Section
if "last_solution" in st.session_state:
    solution = st.session_state["last_solution"]
    val = st.session_state["last_validation"]
    metrics = st.session_state["last_metrics"]
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📈 Solution Diagnostics & Audit")
    
    # KPI Grid
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    with kpi1:
        st.metric("Total Travel Distance", f"{solution.total_distance:,.2f}")
    with kpi2:
        st.metric("Total Travel Duration", f"{solution.total_duration:,.2f}")
    with kpi3:
        st.metric("Dispatched Fleet", f"{solution.vehicles_used} / {len(instance.vehicles)} trucks")
    with kpi4:
        st.metric("Capacity Utilization", f"{metrics.capacity_utilization * 100:.1f}%")
    with kpi5:
        st.metric("Execution Time", f"{solution.runtime_seconds:.2f}s")

    # Status Pill
    if val.overall_feasible:
        st.markdown("""
        <div style="background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.4); border-radius: 8px; padding: 10px 16px; margin: 12px 0; color: #4ADE80; font-weight: 600;">
            ✓ Solution Status: FEASIBLE — Validated by Independent Constraint Auditor
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 8px; padding: 10px 16px; margin: 12px 0; color: #F87171; font-weight: 600;">
            ✗ Solution Status: INFEASIBLE — Issues found in validation check
        </div>
        """, unsafe_allow_html=True)
        for err in val.errors:
            st.error(f"• {err}")

    # Route Table
    st.markdown("#### Vehicle Route Schedules")
    routes_rows = []
    for r in solution.routes:
        routes_rows.append({
            "Vehicle ID": r.vehicle_id,
            "Customers Visited": len(r.customer_ids),
            "Sequence": "Depot ➜ " + " ➜ ".join(r.customer_ids) + " ➜ Depot",
            "Route Distance": round(r.distance, 2),
            "Route Duration": round(r.duration, 2),
            "Total Load": round(r.load, 1),
            "Vehicle Capacity": instance.vehicles[0].capacity,
        })
    st.dataframe(pd.DataFrame(routes_rows), use_container_width=True)

    # Actions
    act1, act2 = st.columns([1, 1])
    with act1:
        st.download_button(
            "📥 Download Solution Manifest (JSON)",
            data=json.dumps(solution.to_dict(), indent=2),
            file_name=f"{instance.metadata.name}_{solution.algorithm}.json",
            mime="application/json",
            use_container_width=True,
        )
    with act2:
        st.markdown("""
        <a href="Route_Map" target="_self" style="text-decoration: none;">
            <div style="background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%); color: white; padding: 9px; border-radius: 10px; text-align: center; font-weight: 600;">
                🗺️ Inspect On Route Map ➜
            </div>
        </a>
        """, unsafe_allow_html=True)
