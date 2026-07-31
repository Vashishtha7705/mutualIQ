"""
Mutual Fund Analytics Platform - Main Streamlit Application Entry.
Provides Executive Overview, Market Indices Tracker, Category Aggregations,
and Navigation Hub.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.config.config_loader import get_config
from src.database.db_manager import get_db_manager
from src.database.query_bank import QueryBank
from src.scoring.fund_scorer import FundScorer
from src.utils.logger import get_logger

logger = get_logger(__name__)

# -----------------------------------------------------------------------------
# Page Configuration & Custom CSS Injection
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="MutualIQ - Fund Analytics Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
    /* Global Theme Overrides */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    /* Glassmorphism Metric Cards */
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        border-color: rgba(99, 102, 241, 0.5);
    }
    .metric-title {
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .metric-value {
        color: #f8fafc;
        font-size: 1.8rem;
        font-weight: 700;
    }
    .metric-delta {
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 4px;
    }
    .delta-positive { color: #10b981; }
    .delta-negative { color: #ef4444; }

    /* Custom Header Banner */
    .header-banner {
        background: linear-gradient(90deg, #4f46e5 0%, #06b6d4 100%);
        border-radius: 16px;
        padding: 30px;
        margin-bottom: 30px;
        color: white;
        box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.4);
    }
    .header-banner h1 {
        margin: 0;
        font-size: 2.4rem;
        font-weight: 800;
        color: #ffffff !important;
    }
    .header-banner p {
        margin-top: 8px;
        font-size: 1.1rem;
        opacity: 0.9;
    }

    /* Sidebar Customization */
    section[data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Data Initialization Helper
# -----------------------------------------------------------------------------
@st.cache_resource
def init_backend():
    db_mgr = get_db_manager()
    qb = QueryBank(db_mgr)
    scorer = FundScorer(db_mgr)
    return qb, scorer

qb, scorer = init_backend()

# -----------------------------------------------------------------------------
# Header Banner
# -----------------------------------------------------------------------------
st.markdown("""
<div class="header-banner">
    <h1>📈 MutualIQ Analytics Platform</h1>
    <p>Institutional-grade Quantitative Mutual Fund Analytics, Star Ratings, XIRR Tracking & AI Portfolio Intelligence</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Executive Key Metrics Dashboard
# -----------------------------------------------------------------------------
st.subheader("📊 Executive Market Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-title">Tracked Schemes</div>
        <div class="metric-value">14,202</div>
        <div class="metric-delta delta-positive">↑ AMFI Direct & Regular</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-title">Nifty 50 TRI CAGR</div>
        <div class="metric-value">13.20%</div>
        <div class="metric-delta delta-positive">↑ Benchmark Base</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-title">Top Category Return</div>
        <div class="metric-value">16.97%</div>
        <div class="metric-delta delta-positive">↑ Equity - Large Cap</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-title">Risk-Free Rate (Rf)</div>
        <div class="metric-value">6.50%</div>
        <div class="metric-delta">RBI 10Y G-Sec Yield</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# -----------------------------------------------------------------------------
# Top Performing Schemes & Category Breakdown
# -----------------------------------------------------------------------------
left_col, right_col = st.columns([6, 4])

with left_col:
    st.subheader("🏆 Top Performing Mutual Funds (5-Star Scored)")
    try:
        df_scored = scorer.score_and_rank_schemes()
        if not df_scored.empty:
            display_cols = [
                "star_rating", "rating_label", "scheme_name", "category_name",
                "composite_score", "cagr_pct", "sharpe_ratio", "max_drawdown_pct"
            ]
            st.dataframe(
                df_scored[display_cols].head(10),
                use_container_width=True,
                column_config={
                    "star_rating": st.column_config.NumberColumn("Stars", format="%d ⭐"),
                    "composite_score": st.column_config.NumberColumn("Score (0-100)", format="%.2f"),
                    "cagr_pct": st.column_config.NumberColumn("CAGR %", format="%.2f%%"),
                    "sharpe_ratio": st.column_config.NumberColumn("Sharpe Ratio", format="%.2f"),
                    "max_drawdown_pct": st.column_config.NumberColumn("Max Drawdown %", format="%.2f%%"),
                },
                hide_index=True
            )
        else:
            st.info("No scored schemes data available. Run ingestion and transformation pipelines.")
    except Exception as exc:
        st.error(f"Error loading scored schemes: {exc}")

with right_col:
    st.subheader("🍰 Category Asset Class Distribution")
    try:
        df_cat = qb.get_category_performance_summary()
        if not df_cat.empty:
            fig = px.pie(
                df_cat,
                values="total_schemes",
                names="category_name",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=10, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No category summary data available.")
    except Exception as exc:
        st.error(f"Error loading category pie chart: {exc}")

st.sidebar.success("Select a detailed module page from the sidebar navigation above 👆")
