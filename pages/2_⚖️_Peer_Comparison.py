"""
Mutual Fund Peer Comparison Page.
Allows multi-fund side-by-side comparisons with radar charts, risk-reward scatter plots,
and quantitative comparison tables.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.analytics.metrics_engine import MetricsEngine
from src.database.db_manager import get_db_manager
from src.scoring.fund_scorer import FundScorer
from src.utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Peer Comparison - MutualIQ", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #f8fafc; }
</style>
""", unsafe_allow_html=True)

st.title("⚖️ Mutual Fund Peer Comparison Tool")

db_mgr = get_db_manager()
scorer = FundScorer(db_mgr)

df_scored = scorer.score_and_rank_schemes()
if df_scored.empty:
    st.warning("No scheme metrics available for peer comparison.")
    st.stop()

scheme_options = {f"{row['scheme_name']} ({row['scheme_code']})": row['scheme_code'] for _, row in df_scored.iterrows()}

selected_schemes = st.multiselect(
    "Select Up to 4 Mutual Funds to Compare Side-by-Side:",
    options=list(scheme_options.keys()),
    default=list(scheme_options.keys())[:min(3, len(scheme_options))]
)

if not selected_schemes:
    st.info("Please select at least 1 mutual fund to view comparison metrics.")
    st.stop()

selected_codes = [scheme_options[s] for s in selected_schemes]
df_comp = df_scored[df_scored["scheme_code"].isin(selected_codes)].copy()

st.subheader("📊 Side-by-Side Quantitative Matrix")
comp_cols = [
    "star_rating", "rating_label", "scheme_name", "category_name",
    "composite_score", "cagr_pct", "sharpe_ratio", "sortino_ratio",
    "max_drawdown_pct", "alpha_pct", "annualized_volatility_pct"
]

st.dataframe(
    df_comp[comp_cols],
    use_container_width=True,
    column_config={
        "star_rating": st.column_config.NumberColumn("Stars", format="%d ⭐"),
        "composite_score": st.column_config.NumberColumn("Score (0-100)", format="%.2f"),
        "cagr_pct": st.column_config.NumberColumn("CAGR %", format="%.2f%%"),
        "sharpe_ratio": st.column_config.NumberColumn("Sharpe", format="%.2f"),
        "sortino_ratio": st.column_config.NumberColumn("Sortino", format="%.2f"),
        "max_drawdown_pct": st.column_config.NumberColumn("Max DD %", format="%.2f%%"),
        "alpha_pct": st.column_config.NumberColumn("Alpha %", format="%.2f%%"),
        "annualized_volatility_pct": st.column_config.NumberColumn("Volatility %", format="%.2f%%"),
    },
    hide_index=True
)

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🎯 Risk vs. Return Matrix (Scatter Plot)")
    fig_scatter = px.scatter(
        df_comp,
        x="annualized_volatility_pct",
        y="cagr_pct",
        color="scheme_name",
        size="composite_score",
        hover_data=["sharpe_ratio", "max_drawdown_pct"],
        labels={"annualized_volatility_pct": "Annualized Volatility (%)", "cagr_pct": "CAGR (%)"},
        title="Risk (Volatility) vs Return (CAGR)"
    )
    fig_scatter.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_scatter, use_container_width=True)

with col_right:
    st.subheader("🕸️ Multi-Factor Quantitative Radar")
    categories = ["CAGR", "Sharpe", "Sortino", "Alpha", "Downside Safety"]

    fig_radar = go.Figure()
    for _, row in df_comp.iterrows():
        # Scaled 0-100 radar metrics
        r_vals = [
            min(100, max(0, float(row["cagr_pct"]))),
            min(100, max(0, float(row["sharpe_ratio"]) * 35)),
            min(100, max(0, float(row["sortino_ratio"]) * 35)),
            min(100, max(0, float(row["alpha_pct"]) * 20)),
            min(100, max(0, 100 - abs(float(row["max_drawdown_pct"])))),
        ]
        fig_radar.add_trace(go.Scatterpolar(
            r=r_vals,
            theta=categories,
            fill='toself',
            name=row["scheme_name"]
        ))

    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_radar, use_container_width=True)
