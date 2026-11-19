"""Delivery Data - Ingestion, sample selection, configuration, and validation."""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys

src_path = Path(__file__).parent.parent.parent / "src"
app_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(app_path))

from routeopt.data import load_delivery_csv, load_cvrplib_instance, load_solomon_instance, validate_instance
from routeopt.data.schema import Vehicle
from ui_theme import apply_custom_css, render_hero

st.set_page_config(page_title="Delivery Data | RouteOpt", page_icon="📁", layout="wide")
apply_custom_css()

render_hero(
    title="📁 Delivery Data Management",
    subtitle="Ingest customer order stops, configure depot and vehicle capacity, or select benchmark instances.",
    badge="Step 1 • Ingestion & Audit"
)

# Tab interface for Data Sources
tab_csv, tab_samples, tab_benchmarks = st.tabs([
    "📤 Upload Custom CSV", 
    "🧪 Built-in Sample Datasets", 
    "🏆 CVRPLIB & Solomon Benchmarks"
])

selected_df = None
instance_source_name = "Custom Upload"

with tab_csv:
    st.markdown("""
    <div style="margin-bottom: 16px;">
        <p style="color: #94A3B8; font-size: 0.95rem;">
            Upload your CSV file with delivery coordinates, customer demands, and optional time windows.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a Delivery CSV",
        type=["csv"],
        help="Expected columns: customer_id, x, y (or lat, lon), demand, [service_time, earliest_time, latest_time]"
    )
    if uploaded_file:
        try:
            selected_df = pd.read_csv(uploaded_file)
            instance_source_name = uploaded_file.name
            st.session_state["raw_csv_df"] = selected_df
        except Exception as e:
            st.error(f"Error reading CSV: {e}")

with tab_samples:
    st.markdown("""
    <p style="color: #94A3B8; font-size: 0.95rem;">
        Quick-start by loading one of our pre-packaged realistic delivery instances.
    </p>
    """, unsafe_allow_html=True)
    
    sample_col1, sample_col2 = st.columns(2)
    with sample_col1:
        if st.button("📦 Load Sample Planar CSV (20 Customers + TW)", use_container_width=True):
            p = Path("data/sample_delivery_data.csv")
            if p.exists():
                selected_df = pd.read_csv(p)
                instance_source_name = "sample_delivery_data.csv"
                st.session_state["raw_csv_df"] = selected_df
                st.success("Loaded 20-stop Planar Sample Instance!")
    with sample_col2:
        if st.button("🌐 Load Sample Geo (SF Lat/Lon, 10 Customers)", use_container_width=True):
            p = Path("data/sample_delivery_geo.csv")
            if p.exists():
                selected_df = pd.read_csv(p)
                instance_source_name = "sample_delivery_geo.csv"
                st.session_state["raw_csv_df"] = selected_df
                st.success("Loaded San Francisco GPS Coordinates Sample!")

with tab_benchmarks:
    st.markdown("""
    <p style="color: #94A3B8; font-size: 0.95rem;">
        Load classic benchmark instances directly from the repository.
    </p>
    """, unsafe_allow_html=True)
    
    b_col1, b_col2 = st.columns(2)
    with b_col1:
        if st.button("🏅 Load CVRPLIB A-n32-k5 (31 Customers, BKS: 784)", use_container_width=True):
            vrp_path = Path("data/raw/benchmark/cvrplib/A-n32-k5.vrp")
            sol_path = Path("data/raw/benchmark/cvrplib/A-n32-k5.sol")
            if vrp_path.exists() and sol_path.exists():
                try:
                    bench_inst = load_cvrplib_instance(vrp_path, sol_path)
                    val_report = validate_instance(bench_inst)
                    st.session_state["instance"] = bench_inst
                    st.session_state["current_instance"] = bench_inst
                    st.session_state["validation_report"] = val_report
                    st.success("CVRPLIB A-n32-k5 Loaded Successfully into Engine!")
                except Exception as e:
                    st.error(f"Error loading benchmark: {e}")
    with b_col2:
        if st.button("⏱️ Load Solomon C101 (25 Customers with Time Windows)", use_container_width=True):
            sol_txt = Path("data/raw/benchmark/solomon/C101.txt")
            if sol_txt.exists():
                try:
                    bench_inst = load_solomon_instance(sol_txt, max_customers=25)
                    val_report = validate_instance(bench_inst)
                    st.session_state["instance"] = bench_inst
                    st.session_state["current_instance"] = bench_inst
                    st.session_state["validation_report"] = val_report
                    st.success("Solomon C101 Loaded Successfully into Engine!")
                except Exception as e:
                    st.error(f"Error loading benchmark: {e}")

# If we have a dataframe from upload or sample selection
if "raw_csv_df" in st.session_state and selected_df is None:
    selected_df = st.session_state["raw_csv_df"]

if selected_df is not None:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"### 📋 Dataset Preview: `{instance_source_name}`")
    
    # Auto-detect coordinates
    is_wgs84 = "lat" in selected_df.columns or "latitude" in selected_df.columns
    
    st.dataframe(selected_df.head(15), use_container_width=True)
    
    # Configuration Box
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🛠️ Instance & Fleet Configuration")
    
    cfg_col1, cfg_col2, cfg_col3 = st.columns(3)
    
    with cfg_col1:
        st.markdown("**1. Coordinate Standard**")
        coord_system = st.selectbox(
            "Coordinate Type",
            ["xy_planar", "wgs84"],
            index=1 if is_wgs84 else 0,
            help="xy_planar for synthetic/benchmark Cartesian coordinates; wgs84 for GPS (lat/lon)"
        )
        
        depot_option = st.radio(
            "Depot Location in CSV",
            ["First row (index 0)", "Last row", "Custom row index"],
            index=0
        )
        if depot_option == "Custom row index":
            depot_row = st.number_input("Row index", min_value=0, max_value=len(selected_df)-1, value=0)
        elif depot_option == "Last row":
            depot_row = len(selected_df) - 1
        else:
            depot_row = 0

    with cfg_col2:
        st.markdown("**2. Fleet Capacity**")
        num_vehicles = st.number_input("Fleet Size (Vehicles)", min_value=1, max_value=100, value=5)
        vehicle_capacity = st.number_input("Capacity per Vehicle", min_value=1, value=100)
        max_route_duration = st.number_input("Max Route Duration (0 = Unlimited)", min_value=0, value=0)

    with cfg_col3:
        st.markdown("**3. Distance & Timing**")
        dist_conv = st.selectbox(
            "Distance Metric",
            ["euclidean_exact", "euclidean_rounded"],
            index=0,
            help="euclidean_exact for precision; euclidean_rounded for standard CVRPLIB TSPLIB rounding."
        )
        default_service_time = st.number_input("Default Service Time (mins)", min_value=0.0, value=10.0)

    # Process and Validate
    if st.button("🚀 Validate & Build Instance Model", type="primary", use_container_width=True):
        with st.spinner("Parsing coordinates, generating distance matrices, and verifying constraints..."):
            try:
                temp_csv = Path("temp_upload.csv")
                selected_df.to_csv(temp_csv, index=False)
                
                instance = load_delivery_csv(
                    temp_csv,
                    depot_row=depot_row,
                    coordinate_system=coord_system,
                    distance_convention=dist_conv,
                )
                
                # Apply custom fleet override if specified
                instance.vehicles = [
                    Vehicle(
                        vehicle_id=f"V{i+1}",
                        capacity=vehicle_capacity,
                        max_route_duration=max_route_duration if max_route_duration > 0 else None
                    )
                    for i in range(num_vehicles)
                ]
                
                report = validate_instance(instance)
                
                st.session_state["instance"] = instance
                st.session_state["current_instance"] = instance
                st.session_state["validation_report"] = report
                st.session_state["df_preview"] = selected_df
                
                st.success("✅ Instance compiled and verified successfully! Head to **Route Optimization** to solve.")
                
            except Exception as e:
                st.error(f"Error parsing instance: {e}")
                st.exception(e)

# Display Validation Report if present
if "validation_report" in st.session_state and "current_instance" in st.session_state:
    report = st.session_state["validation_report"]
    inst = st.session_state["current_instance"]
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📊 Active Model Summary")
    
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Customers", inst.num_customers)
    with m2:
        st.metric("Fleet Vehicles", len(inst.vehicles))
    with m3:
        st.metric("Total Demand", f"{inst.total_demand:,.0f}")
    with m4:
        st.metric("Total Fleet Cap", f"{inst.total_capacity:,.0f}")
    with m5:
        util = (inst.total_demand / inst.total_capacity) * 100 if inst.total_capacity > 0 else 0
        st.metric("Required Fleet Util.", f"{util:.1f}%")

    if report.is_valid:
        st.markdown("""
        <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); padding: 12px 16px; border-radius: 8px; margin-top: 12px; color: #4ADE80;">
            ✓ <strong>Integrity Verified:</strong> All node coordinates, vehicle limits, and non-negative demand constraints passed inspection.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error("Validation detected issues in the dataset:")
        for err in report.errors:
            st.error(f"• {err}")
            
    if report.warnings:
        for warn in report.warnings:
            st.warning(f"⚠️ {warn}")
