"""Route Map - Interactive Plotly Geographic and Planar Visualization."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys

src_path = Path(__file__).parent.parent.parent / "src"
app_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(app_path))

from ui_theme import apply_custom_css, render_hero

st.set_page_config(page_title="Route Map | RouteOpt", page_icon="🗺️", layout="wide")
apply_custom_css()

render_hero(
    title="🗺️ Interactive Route Cartography",
    subtitle="Visualize stop sequencing, vehicle circuits, loads, and geographic coverage on an interactive canvas.",
    badge="Step 3 • Spatial Visualizer"
)

# Guard checks
if "last_solution" not in st.session_state or "current_instance" not in st.session_state:
    st.markdown("""
    <div class="glass-card" style="text-align: center; padding: 40px;">
        <h3 style="color: #F87171; margin-bottom: 8px;">⚠️ No Solved Solution Found</h3>
        <p style="color: #94A3B8; font-size: 1rem; max-width: 500px; margin: 0 auto 20px auto;">
            Please run an optimization on the <strong>Route Optimization</strong> page to generate interactive route paths.
        </p>
        <a href="Route_Optimization" target="_self" style="text-decoration: none;">
            <span class="status-pill pill-info" style="font-size: 0.95rem; padding: 8px 18px;">👉 Go to Optimization</span>
        </a>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

solution = st.session_state["last_solution"]
instance = st.session_state["current_instance"]

is_geo = instance.metadata.coordinate_system == "wgs84"

# Summary Strip
st.markdown(f"""
<div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px 20px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
    <div>
        <span style="color: #64748B; font-size: 0.8rem; text-transform: uppercase;">Instance / Method</span>
        <div style="color: #F1F5F9; font-weight: 700;">{instance.metadata.name} • {solution.algorithm}</div>
    </div>
    <div style="display: flex; gap: 24px;">
        <div>
            <span style="color: #64748B; font-size: 0.8rem;">Active Circuits</span>
            <div style="color: #38BDF8; font-weight: 700;">{len(solution.routes)} Routes</div>
        </div>
        <div>
            <span style="color: #64748B; font-size: 0.8rem;">Total Distance</span>
            <div style="color: #818CF8; font-weight: 700;">{solution.total_distance:.2f}</div>
        </div>
        <div>
            <span style="color: #64748B; font-size: 0.8rem;">Total Time</span>
            <div style="color: #34D399; font-weight: 700;">{solution.total_duration:.2f}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Generate Plotly Figure
fig = go.Figure()

# Palette for routes
palette = [
    "#38BDF8", "#F43F5E", "#10B981", "#F59E0B", 
    "#8B5CF6", "#EC4899", "#14B8A6", "#6366F1",
    "#FB923C", "#A855F7", "#4ADE80", "#06B6D4"
]

for i, route in enumerate(solution.routes):
    color = palette[i % len(palette)]
    
    # Coordinates list starting at depot
    route_coords = [(instance.depot.x, instance.depot.y)]
    for cust_id in route.customer_ids:
        c = next(cust for cust in instance.customers if cust.customer_id == cust_id)
        route_coords.append((c.x, c.y))
    route_coords.append((instance.depot.x, instance.depot.y))
    
    xs, ys = zip(*route_coords)
    
    # Route path line
    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="lines+markers",
        line=dict(color=color, width=3),
        marker=dict(size=7, color=color, symbol="circle"),
        name=f"{route.vehicle_id} ({len(route.customer_ids)} stops)",
        hovertemplate=(
            f"<b>{route.vehicle_id}</b><br>"
            "Distance: " + f"{route.distance:.1f}<br>"
            "Load: " + f"{route.load:.0f}<extra></extra>"
        ),
    ))
    
    # Stop sequence annotations
    for step_num, (x, y) in enumerate(route_coords):
        if step_num not in (0, len(route_coords) - 1):
            fig.add_trace(go.Scatter(
                x=[x], y=[y],
                mode="text",
                text=[f"#{step_num}"],
                textposition="bottom center",
                textfont=dict(size=10, color=color, family="Inter, sans-serif"),
                showlegend=False,
                hoverinfo="skip"
            ))

# Depot Marker
fig.add_trace(go.Scatter(
    x=[instance.depot.x], y=[instance.depot.y],
    mode="markers+text",
    marker=dict(size=18, color="#F59E0B", symbol="star", line=dict(color="#FFFFFF", width=2)),
    text=["DEPOT"],
    textposition="top center",
    textfont=dict(size=13, color="#F59E0B", family="Inter, sans-serif"),
    name="Depot Hub",
    hovertemplate="<b>Central Distribution Depot</b><extra></extra>"
))

# Customers Markers
cust_xs = [c.x for c in instance.customers]
cust_ys = [c.y for c in instance.customers]
cust_texts = [f"Stop {c.customer_id}" for c in instance.customers]
cust_hover = [
    f"<b>Customer {c.customer_id}</b><br>Demand: {c.demand}<br>Earliest: {c.earliest_time or 0}<br>Latest: {c.latest_time or '∞'}"
    for c in instance.customers
]

fig.add_trace(go.Scatter(
    x=cust_xs, y=cust_ys,
    mode="markers",
    marker=dict(size=10, color="#94A3B8", symbol="circle", line=dict(color="#1E293B", width=1.5)),
    text=cust_texts,
    customdata=cust_hover,
    hovertemplate="%{customdata}<extra></extra>",
    name="Customer Delivery Points"
))

# Layout Styling
fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(15, 23, 42, 0.8)",
    plot_bgcolor="rgba(15, 23, 42, 0.9)",
    font=dict(family="Inter, sans-serif", color="#F8FAFC"),
    height=680,
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis=dict(
        title="Longitude" if is_geo else "Planar X Coordinate",
        gridcolor="rgba(255, 255, 255, 0.06)",
        zerolinecolor="rgba(255, 255, 255, 0.1)"
    ),
    yaxis=dict(
        title="Latitude" if is_geo else "Planar Y Coordinate",
        gridcolor="rgba(255, 255, 255, 0.06)",
        zerolinecolor="rgba(255, 255, 255, 0.1)",
        scaleanchor="x" if not is_geo else None,
        scaleratio=1 if not is_geo else None
    ),
    legend=dict(
        bgcolor="rgba(30, 41, 59, 0.8)",
        bordercolor="rgba(255, 255, 255, 0.1)",
        borderwidth=1,
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    hovermode="closest"
)

st.plotly_chart(fig, use_container_width=True)

# Turn-by-turn itinerary expander
with st.expander("🔍 Detailed Stop-by-Stop Itinerary", expanded=True):
    itin_tabs = st.tabs([f"Vehicle {r.vehicle_id}" for r in solution.routes])
    for idx, (tab, r) in enumerate(zip(itin_tabs, solution.routes)):
        with tab:
            stops = [{"Sequence": 0, "Stop ID": "Depot", "Arrival": 0, "Departure": 0, "Current Load": r.load}]
            cur_load = r.load
            for seq, (c_id, arr, dep) in enumerate(zip(r.customer_ids, r.arrival_times, r.departure_times), 1):
                c = next(cust for cust in instance.customers if cust.customer_id == c_id)
                cur_load -= c.demand
                stops.append({
                    "Sequence": seq,
                    "Stop ID": c_id,
                    "Arrival": f"{arr:.1f}",
                    "Departure": f"{dep:.1f}",
                    "Demand Delivered": c.demand,
                    "Remaining Load": f"{cur_load:.1f}",
                })
            stops.append({
                "Sequence": len(r.customer_ids) + 1,
                "Stop ID": "Depot Return",
                "Arrival": f"{r.duration:.1f}",
                "Departure": "-",
                "Current Load": 0
            })
            st.dataframe(pd.DataFrame(stops), use_container_width=True)
