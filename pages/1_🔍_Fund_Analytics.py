"""
Fund Analytics Explorer Page.
Provides single-scheme deep-dive analytics with interactive Plotly charts,
rolling return time series, drawdown charts, and 18 quantitative metric cards.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.analytics.metrics_engine import MetricsEngine
from src.analytics.rolling_analytics import RollingAnalyticsEngine
from src.database.db_manager import get_db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Fund Analytics - MutualIQ", page_icon="🔍", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #f8fafc; }
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .metric-title { color: #94a3b8; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; }
    .metric-val { color: #f8fafc; font-size: 1.4rem; font-weight: 700; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

st.title("🔍 Mutual Fund Analytics Explorer")

db_mgr = get_db_manager()
metrics_engine = MetricsEngine()
rolling_engine = RollingAnalyticsEngine()

# Fetch list of schemes
with db_mgr.get_session() as session:
    df_schemes = pd.read_sql("SELECT scheme_code, scheme_name FROM dim_scheme ORDER BY scheme_name ASC", session.bind)

if df_schemes.empty:
    st.warning("No scheme records found in database.")
    st.stop()

scheme_option_map = {f"{row['scheme_name']} ({row['scheme_code']})": row['scheme_code'] for _, row in df_schemes.iterrows()}
selected_option = st.selectbox("Select Mutual Fund Scheme:", list(scheme_option_map.keys()))
selected_code = scheme_option_map[selected_option]

# Fetch daily NAV and benchmark series
with db_mgr.get_session() as session:
    df_nav = pd.read_sql(
        "SELECT full_date AS date, nav, daily_return, cumulative_return, rolling_30d_volatility FROM fact_daily_nav f JOIN dim_date d ON f.date_id = d.date_id WHERE f.scheme_code = :code ORDER BY date ASC",
        session.bind,
        params={"code": selected_code}
    )
    df_bench = pd.read_sql(
        "SELECT full_date AS date, close_value AS benchmark_close, daily_return FROM fact_benchmark_index b JOIN dim_date d ON b.date_id = d.date_id WHERE b.index_name = 'NIFTY_50_TRI' ORDER BY date ASC",
        session.bind
    )

if df_nav.empty:
    st.error("No daily NAV records available for selected scheme.")
    st.stop()

# Compute metrics
metrics = metrics_engine.compute_full_scheme_metrics(df_nav, df_bench)

# Render 18 Metric Cards in a Grid
st.subheader(f"📊 Quantitative Risk & Return Profile: {selected_option}")

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.markdown(f'<div class="metric-card"><div class="metric-title">CAGR (3Y+)</div><div class="metric-val">{metrics.get("cagr_pct", 0)}%</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Sharpe Ratio</div><div class="metric-val">{metrics.get("sharpe_ratio", 0)}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Sortino Ratio</div><div class="metric-val">{metrics.get("sortino_ratio", 0)}</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Max Drawdown</div><div class="metric-val">{metrics.get("max_drawdown_pct", 0)}%</div></div>', unsafe_allow_html=True)
with c5:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Jensen\'s Alpha</div><div class="metric-val">{metrics.get("alpha_pct", 0)}%</div></div>', unsafe_allow_html=True)
with c6:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Beta (β)</div><div class="metric-val">{metrics.get("beta", 1.0)}</div></div>', unsafe_allow_html=True)

c7, c8, c9, c10, c11, c12 = st.columns(6)
with c7:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Ann. Volatility</div><div class="metric-val">{metrics.get("annualized_volatility_pct", 0)}%</div></div>', unsafe_allow_html=True)
with c8:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Downside Vol.</div><div class="metric-val">{metrics.get("downside_volatility_pct", 0)}%</div></div>', unsafe_allow_html=True)
with c9:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Calmar Ratio</div><div class="metric-val">{metrics.get("calmar_ratio", 0)}</div></div>', unsafe_allow_html=True)
with c10:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Tracking Error</div><div class="metric-val">{metrics.get("tracking_error_pct", 0)}%</div></div>', unsafe_allow_html=True)
with c11:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Information Ratio</div><div class="metric-val">{metrics.get("information_ratio", 0)}</div></div>', unsafe_allow_html=True)
with c12:
    st.markdown(f'<div class="metric-card"><div class="metric-title">VaR (95% Daily)</div><div class="metric-val">{metrics.get("var_95_daily_pct", 0)}%</div></div>', unsafe_allow_html=True)

st.markdown("---")

# Interactive Charts
tab1, tab2, tab3 = st.tabs(["📈 NAV Growth vs Benchmark", "🔄 Rolling Returns (1Y / 3Y)", "📉 Peak-to-Trough Drawdowns"])

with tab1:
    st.subheader("Historical NAV Growth Series")
    fig_nav = px.line(df_nav, x="date", y="nav", title=f"{selected_option} NAV Growth", line_shape="spline")
    fig_nav.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_nav, use_container_width=True)

with tab2:
    st.subheader("Rolling CAGR Performance")
    df_rolling = rolling_engine.compute_rolling_returns(df_nav, window_years=[1, 3])
    fig_roll = px.line(df_rolling, x="date", y=["rolling_1y_cagr", "rolling_3y_cagr"], title="Rolling 1-Year & 3-Year CAGR %")
    fig_roll.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_roll, use_container_width=True)

with tab3:
    st.subheader("Historical Drawdown %")
    df_dd = rolling_engine.compute_drawdown_series(df_nav)
    fig_dd = px.area(df_dd, x="date", y="drawdown_pct", title="Peak-to-Trough Drawdown %", color_discrete_sequence=["#ef4444"])
    fig_dd.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_dd, use_container_width=True)
