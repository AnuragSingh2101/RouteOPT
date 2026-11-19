"""Scenario Analysis - Modern Monte Carlo & Sensitivity Simulation Suite."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import time

src_path = Path(__file__).parent.parent.parent / "src"
app_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(app_path))

from routeopt.scenarios import (
    ScenarioConfig, CoordinateDistribution,
    create_scenario_instance, create_scenario_config,
    SCENARIO_TEMPLATES, get_template,
)
from routeopt.optimization import solve_cvrp_ortools, ORToolsSolverConfig
from routeopt.algorithms import clarke_wright_savings
from ui_theme import apply_custom_css, render_hero

st.set_page_config(page_title="Scenario Analysis | RouteOpt", page_icon="🔬", layout="wide")
apply_custom_css()

render_hero(
    title="🔬 Monte Carlo Scenario & Sensitivity Analysis",
    subtitle="Simulate fleet stress tests, evaluate customer scale boundaries, and analyze capacity constraints under synthetic stochastic variations.",
    badge="Step 5 • Stress Testing"
)

# 1. Base Configuration Selector
st.markdown("### 1. Base Scenario Archetype")
template_options = list(SCENARIO_TEMPLATES.keys()) + ["Custom Archetype"]
chosen_template = st.selectbox("Select Predefined Scenario", template_options)

if chosen_template != "Custom Archetype":
    base_config = get_template(chosen_template)
    st.markdown(f"""
    <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 12px 18px; margin-bottom: 20px; display: flex; gap: 24px; flex-wrap: wrap;">
        <div><span style="color:#64748B; font-size:0.8rem;">Customers</span><div style="color:#38BDF8; font-weight:700;">{base_config.num_customers}</div></div>
        <div><span style="color:#64748B; font-size:0.8rem;">Fleet Count</span><div style="color:#818CF8; font-weight:700;">{base_config.num_vehicles}</div></div>
        <div><span style="color:#64748B; font-size:0.8rem;">Capacity</span><div style="color:#A78BFA; font-weight:700;">{base_config.vehicle_capacity}</div></div>
        <div><span style="color:#64748B; font-size:0.8rem;">Spatial Pattern</span><div style="color:#34D399; font-weight:700;">{base_config.coord_distribution.value}</div></div>
    </div>
    """, unsafe_allow_html=True)
else:
    c_custom1, c_custom2 = st.columns(2)
    with c_custom1:
        num_cust = st.number_input("Base Customer Count", 5, 100, 25)
        num_veh = st.number_input("Base Fleet Size", 1, 25, 5)
        v_cap = st.number_input("Base Vehicle Capacity", 10, 500, 100)
    with c_custom2:
        coord_dist = st.selectbox("Spatial Distribution", [c.value for c in CoordinateDistribution])
        demand_dist = st.selectbox("Demand Distribution", ["uniform", "normal", "bimodal"])
        tw_density = st.slider("Time Window Proportion", 0.0, 1.0, 0.2)

    base_config = create_scenario_config(
        num_customers=num_cust,
        num_vehicles=num_veh,
        vehicle_capacity=v_cap,
        coord_distribution=coord_dist,
        time_window_density=tw_density,
        demand_distribution=demand_dist,
    )

# 2. Parameter Variation
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### 2. Sensitivity Target Parameter")

param_options = {
    "num_customers": "Customer Order Scale (Stop Count)",
    "vehicle_capacity": "Vehicle Payload Capacity",
    "num_vehicles": "Total Available Fleet Size",
    "cluster_std": "Geographic Cluster Dispersion (Density)",
}
param_target = st.selectbox("Select Parameter to Sweep", list(param_options.keys()), format_func=lambda x: param_options[x])

col_val1, col_val2 = st.columns(2)
with col_val1:
    if param_target == "num_customers":
        val_input = st.text_input("Values to Test (comma-separated)", "10, 20, 30, 40, 50")
        sweep_values = [int(v.strip()) for v in val_input.split(",") if v.strip().isdigit()]
    elif param_target == "vehicle_capacity":
        val_input = st.text_input("Values to Test (comma-separated)", "50, 75, 100, 150, 200")
        sweep_values = [float(v.strip()) for v in val_input.split(",") if v.strip()]
    elif param_target == "num_vehicles":
        val_input = st.text_input("Values to Test (comma-separated)", "3, 5, 8, 10, 12")
        sweep_values = [int(v.strip()) for v in val_input.split(",") if v.strip().isdigit()]
    else:
        val_input = st.text_input("Values to Test (comma-separated)", "5, 10, 15, 20")
        sweep_values = [float(v.strip()) for v in val_input.split(",") if v.strip()]

with col_val2:
    seeds_count = st.slider("Monte Carlo Repetitions per Value (Seeds)", 1, 5, 2, help="Tests multiple pseudo-random distributions for statistical rigor")
    solver_choice = st.radio("Simulation Engine", ["Clarke-Wright Savings (High Speed)", "OR-Tools (Exact/Metaheuristic)"], horizontal=True)

# 3. Execution
if st.button("🚀 Run Monte Carlo Sweep", type="primary", use_container_width=True):
    if len(sweep_values) < 2:
        st.error("Please enter at least 2 sweep points.")
        st.stop()

    progress_bar = st.progress(0.0)
    status_label = st.empty()
    
    total_iterations = len(sweep_values) * seeds_count
    counter = 0
    results_records = []

    for v_idx, val in enumerate(sweep_values):
        for s_idx in range(seeds_count):
            counter += 1
            progress_bar.progress(counter / total_iterations)
            status_label.text(f"Running simulation: {param_target}={val} | Iteration {s_idx+1}/{seeds_count} ({counter}/{total_iterations})")

            cfg_dict = base_config.__dict__.copy()
            cfg_dict[param_target] = val
            cfg_dict["seed"] = 100 + s_idx * 50 + v_idx * 7
            cfg_dict["instance_name"] = f"mc_{param_target}_{val}_s{s_idx}"

            test_inst_cfg = ScenarioConfig(**cfg_dict)
            
            try:
                inst = create_scenario_instance(test_inst_cfg)
                t_start = time.time()
                
                if "OR-Tools" in solver_choice:
                    c = ORToolsSolverConfig(time_limit_seconds=5)
                    sol = solve_cvrp_ortools(inst, inst.distance_matrix, config=c)
                else:
                    sol = clarke_wright_savings(inst, inst.distance_matrix)
                
                t_dur = time.time() - t_start

                results_records.append({
                    "param_target": param_target,
                    "param_value": val,
                    "seed": test_inst_cfg.seed,
                    "total_distance": sol.total_distance,
                    "total_duration": sol.total_duration,
                    "vehicles_used": sol.vehicles_used,
                    "feasible": sol.status == "feasible",
                    "runtime_sec": t_dur
                })
            except Exception as e:
                pass

    progress_bar.empty()
    status_label.empty()

    if results_records:
        df_sim = pd.DataFrame(results_records)
        st.session_state["simulation_results"] = df_sim
        st.success(f"Completed {len(df_sim)} simulation runs across parameter sweep!")

# Results Display
if "simulation_results" in st.session_state:
    df_sim = st.session_state["simulation_results"]
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📊 Simulation Findings & Response Curves")

    tab1, tab2, tab3 = st.tabs(["📈 Distance Response", "🚚 Fleet Utilization", "📋 Raw Data"])

    with tab1:
        fig_curve = px.line(
            df_sim.groupby("param_value")["total_distance"].mean().reset_index(),
            x="param_value", y="total_distance",
            markers=True,
            title=f"Impact of {param_options.get(param_target, param_target)} on Total Mileage",
            labels={"param_value": param_target, "total_distance": "Average Fleet Distance"},
            template="plotly_dark"
        )
        fig_curve.add_scatter(
            x=df_sim["param_value"], y=df_sim["total_distance"],
            mode="markers", name="Individual Monte Carlo Samples",
            marker=dict(opacity=0.4, color="#38BDF8")
        )
        fig_curve.update_layout(paper_bgcolor="rgba(15, 23, 42, 0.5)", plot_bgcolor="rgba(15, 23, 42, 0.5)")
        st.plotly_chart(fig_curve, use_container_width=True)

    with tab2:
        fig_veh = px.box(
            df_sim, x="param_value", y="vehicles_used",
            title=f"Vehicle Requirements by {param_options.get(param_target, param_target)}",
            labels={"param_value": param_target, "vehicles_used": "Active Trucks Dispatched"},
            template="plotly_dark"
        )
        fig_veh.update_layout(paper_bgcolor="rgba(15, 23, 42, 0.5)", plot_bgcolor="rgba(15, 23, 42, 0.5)")
        st.plotly_chart(fig_veh, use_container_width=True)

    with tab3:
        st.dataframe(df_sim, use_container_width=True)
        st.download_button(
            "📥 Export Simulation CSV",
            data=df_sim.to_csv(index=False),
            file_name=f"monte_carlo_sensitivity_{param_target}.csv",
            mime="text/csv"
        )
