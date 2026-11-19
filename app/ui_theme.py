"""Shared UI styling and reusable components for RouteOpt dashboard."""

import streamlit as st

def apply_custom_css():
    """Apply unified, premium, modern CSS across all RouteOpt pages."""
    st.markdown("""
    <style>
        /* Import Google Inter Font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            letter-spacing: -0.01em;
        }

        /* Top Header Styling */
        .hero-banner {
            background: linear-gradient(135deg, rgba(37, 99, 235, 0.12) 0%, rgba(14, 165, 233, 0.08) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 28px 32px;
            margin-bottom: 24px;
            box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.25);
            backdrop-filter: blur(8px);
        }

        .hero-title {
            font-size: 2.25rem;
            font-weight: 800;
            background: linear-gradient(135deg, #60A5FA 0%, #38BDF8 50%, #818CF8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
            letter-spacing: -0.02em;
        }

        .hero-subtitle {
            font-size: 1.05rem;
            color: #94A3B8;
            font-weight: 400;
            line-height: 1.5;
            margin-bottom: 0;
        }

        /* Cards and Containers */
        .glass-card {
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 22px 24px;
            margin-bottom: 18px;
            box-shadow: 0 4px 16px -2px rgba(0, 0, 0, 0.2);
            transition: all 0.25s ease-in-out;
        }
        
        .glass-card:hover {
            border-color: rgba(96, 165, 250, 0.3);
            box-shadow: 0 8px 24px -4px rgba(37, 99, 235, 0.15);
            transform: translateY(-1px);
        }

        .card-header {
            font-size: 1.15rem;
            font-weight: 600;
            color: #F1F5F9;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Metrics styling */
        div[data-testid="stMetric"] {
            background: rgba(30, 41, 59, 0.75) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            padding: 16px 20px !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15) !important;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }

        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border-color: rgba(56, 189, 248, 0.4) !important;
        }

        div[data-testid="stMetric"] label {
            color: #94A3B8 !important;
            font-size: 0.85rem !important;
            font-weight: 500 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
        }

        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
            color: #F8FAFC !important;
            font-weight: 700 !important;
            font-size: 1.75rem !important;
        }

        /* Badge Pills */
        .status-pill {
            display: inline-flex;
            align-items: center;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.825rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        .pill-success {
            background: rgba(34, 197, 94, 0.15);
            color: #4ADE80;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }

        .pill-danger {
            background: rgba(239, 68, 68, 0.15);
            color: #F87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .pill-info {
            background: rgba(59, 130, 246, 0.15);
            color: #60A5FA;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }

        .pill-warning {
            background: rgba(234, 179, 8, 0.15);
            color: #FACC15;
            border: 1px solid rgba(234, 179, 8, 0.3);
        }

        /* Buttons refinement */
        .stButton>button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            padding: 8px 20px !important;
            transition: all 0.2s ease !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }

        .stButton>button[kind="primary"] {
            background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
            border: none !important;
        }

        .stButton>button[kind="primary"]:hover {
            background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5) !important;
            transform: translateY(-1px);
        }

        /* Download button styling */
        .stDownloadButton>button {
            border-radius: 10px !important;
            background: rgba(30, 41, 59, 0.8) !important;
            border: 1px solid rgba(56, 189, 248, 0.4) !important;
            color: #38BDF8 !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }

        .stDownloadButton>button:hover {
            background: rgba(56, 189, 248, 0.1) !important;
            border-color: #38BDF8 !important;
            transform: translateY(-1px);
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #0B1120 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
        }

        /* Tables & Dataframes */
        .stDataFrame {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        /* File Uploader */
        div[data-testid="stFileUploader"] {
            background: rgba(30, 41, 59, 0.4);
            border-radius: 14px;
            border: 2px dashed rgba(255, 255, 255, 0.15);
            padding: 16px;
            transition: border-color 0.2s ease;
        }

        div[data-testid="stFileUploader"]:hover {
            border-color: #38BDF8;
        }

        /* Custom scrollbars */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #0F172A;
        }
        ::-webkit-scrollbar-thumb {
            background: #334155;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #475569;
        }
    </style>
    """, unsafe_allow_html=True)


def render_hero(title: str, subtitle: str, badge: str = "RouteOpt Engine v0.1"):
    """Render consistent modern hero banner at top of page."""
    st.markdown(f"""
    <div class="hero-banner">
        <span class="status-pill pill-info" style="margin-bottom: 12px;">{badge}</span>
        <div class="hero-title">{title}</div>
        <p class="hero-subtitle">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def render_card(title: str, content: str = ""):
    """Helper to start an aesthetically styled card container."""
    st.markdown(f"""
    <div class="glass-card">
        <div class="card-header">{title}</div>
        {content}
    </div>
    """, unsafe_allow_html=True)
