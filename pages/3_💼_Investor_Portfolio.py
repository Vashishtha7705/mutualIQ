"""
Investor Portfolio & SIP Simulator Page.
Displays investor holdings, unrealized PnL, XIRR %, asset allocation pie chart,
and interactive SIP goal simulator.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from src.analytics.portfolio import PortfolioTracker
from src.database.db_manager import get_db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Investor Portfolio - MutualIQ", page_icon="💼", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #f8fafc; }
    .card { background: rgba(30, 41, 59, 0.7); border-radius: 12px; padding: 18px; border: 1px solid rgba(255,255,255,0.1); }
    .title { color: #94a3b8; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; }
    .val { color: #f8fafc; font-size: 1.8rem; font-weight: 700; }
    .positive { color: #10b981; }
    .negative { color: #ef4444; }
</style>
""", unsafe_allow_html=True)

st.title("💼 Investor Portfolio Tracker & SIP Simulator")

db_mgr = get_db_manager()
tracker = PortfolioTracker(db_mgr)

# Fetch investors
with db_mgr.get_session() as session:
    df_investors = pd.read_sql("SELECT investor_id, investor_name, risk_profile, city FROM dim_investor ORDER BY investor_name ASC", session.bind)

if df_investors.empty:
    st.warning("No investor records found.")
    st.stop()

inv_map = {f"{row['investor_name']} ({row['risk_profile']} - {row['city']})": row['investor_id'] for _, row in df_investors.iterrows()}
selected_inv = st.selectbox("Select Investor Profile:", list(inv_map.keys()))
inv_id = inv_map[selected_inv]

report = tracker.get_portfolio_summary_report(inv_id)

if not report or not report.get("holdings"):
    st.info("No active holdings found for selected investor.")
else:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="card"><div class="title">Total Invested</div><div class="val">₹{report["total_invested_amount"]:,.2f}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="card"><div class="title">Current Valuation</div><div class="val">₹{report["total_current_value"]:,.2f}</div></div>', unsafe_allow_html=True)
    with col3:
        pnl_cls = "positive" if report["total_pnl"] >= 0 else "negative"
        st.markdown(f'<div class="card"><div class="title">Unrealized PnL</div><div class="val {pnl_cls}">₹{report["total_pnl"]:,.2f} ({report["total_return_pct"]}%)</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="card"><div class="title">Portfolio XIRR %</div><div class="val positive">{report["xirr_pct"]}%</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    left_c, right_c = st.columns([6, 4])
    with left_c:
        st.subheader("📋 Current Holdings Detail")
        df_h = pd.DataFrame(report["holdings"])
        st.dataframe(
            df_h[["scheme_name", "category_name", "invested_amount", "units_held", "current_nav", "current_value", "pnl", "return_pct"]],
            use_container_width=True,
            column_config={
                "invested_amount": st.column_config.NumberColumn("Invested ₹", format="₹%.2f"),
                "current_value": st.column_config.NumberColumn("Valuation ₹", format="₹%.2f"),
                "pnl": st.column_config.NumberColumn("PnL ₹", format="₹%.2f"),
                "return_pct": st.column_config.NumberColumn("Return %", format="%.2f%%"),
            },
            hide_index=True
        )

    with right_c:
        st.subheader("🍕 Asset Allocation Drift")
        df_alloc = pd.DataFrame(report["asset_allocation"])
        fig_pie = px.pie(df_alloc, values="current_value", names="asset_class", hole=0.4, title="Asset Class Breakdown")
        fig_pie.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

# Interactive SIP Goal Simulator
st.subheader("🧮 Interactive SIP Future Wealth Simulator")
sim_col1, sim_col2, sim_col3 = st.columns(3)

with sim_col1:
    monthly_sip = st.slider("Monthly SIP Amount (₹):", min_value=1000, max_value=100000, value=10000, step=1000)
with sim_col2:
    investment_years = st.slider("Duration (Years):", min_value=1, max_value=30, value=10, step=1)
with sim_col3:
    expected_return_pct = st.slider("Expected Annual CAGR (%):", min_value=5.0, max_value=25.0, value=12.0, step=0.5)

# Future Value formula for SIP: FV = P * [ ((1+r)^n - 1) / r ] * (1+r)
r = (expected_return_pct / 100.0) / 12.0
n = investment_years * 12
total_invested_sim = monthly_sip * n
fv_sim = monthly_sip * (((1 + r) ** n - 1) / r) * (1 + r)
wealth_gain_sim = fv_sim - total_invested_sim

r_col1, r_col2, r_col3 = st.columns(3)
with r_col1:
    st.metric("Total Investment", f"₹{total_invested_sim:,.0f}")
with r_col2:
    st.metric("Estimated Wealth Gain", f"₹{wealth_gain_sim:,.0f}")
with r_col3:
    st.metric("Expected Future Portfolio Value", f"₹{fv_sim:,.0f}")
