"""
AI Fund Recommendation Engine Page.
Provides interactive risk profiling and personalized 5-Star model portfolio recommendations.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from src.database.db_manager import get_db_manager
from src.scoring.fund_scorer import FundScorer
from src.scoring.recommendation import RecommendationEngine
from src.utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="AI Fund Recommendation - MutualIQ", page_icon="🤖", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #f8fafc; }
    .rec-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 15px;
    }
    .rec-title { font-size: 1.2rem; font-weight: 700; color: #818cf8; }
    .badge { background: #312e81; color: #c7d2fe; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

st.title("🤖 AI Mutual Fund Recommendation Engine")

db_mgr = get_db_manager()
scorer = FundScorer(db_mgr)
rec_engine = RecommendationEngine(scorer)

st.markdown("### 🎯 Interactive Investor Risk Profiler")

c_risk, c_stars, c_btn = st.columns([4, 4, 2])

with c_risk:
    risk_profile = st.selectbox(
        "Select Your Investment Risk Profile:",
        options=["Aggressive", "Moderate", "Conservative"],
        index=0
    )

with c_stars:
    min_stars = st.slider("Minimum Acceptable Star Rating:", min_value=1, max_value=5, value=4, step=1)

with c_btn:
    st.write("")
    st.write("")
    generate_btn = st.button("🚀 Generate Portfolio", use_container_width=True)

rec = rec_engine.get_recommendations_for_profile(
    risk_profile=risk_profile,
    min_star_rating=min_stars
)

if rec and rec.get("recommended_schemes"):
    st.subheader(f"🌟 Recommended 5-Star Model Portfolio ({risk_profile} Profile)")

    col_left, col_right = st.columns([6, 4])

    with col_left:
        for scheme in rec["recommended_schemes"]:
            st.markdown(f"""
            <div class="rec-card">
                <div class="rec-title">{scheme["scheme_name"]} <span class="badge">{scheme["rating_label"]}</span></div>
                <p style="margin-top:5px; color:#94a3b8;">
                    <b>Category:</b> {scheme["category_name"]} | <b>Fund House:</b> {scheme["fund_house_name"]}<br>
                    <b>Composite Score:</b> {scheme["composite_score"]} / 100 | <b>3Y CAGR:</b> {scheme["cagr_pct"]}% | <b>Sharpe Ratio:</b> {scheme["sharpe_ratio"]}
                </p>
                <div style="background:#1e1b4b; padding:8px 12px; border-radius:8px; display:inline-block; font-weight:600; color:#a5b4fc;">
                    Suggested Portfolio Weight: {scheme["suggested_category_weight_pct"]}%
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_right:
        st.subheader("🎯 Model Asset Allocation Targets")
        df_alloc = pd.DataFrame(list(rec["model_portfolio_allocation"].items()), columns=["Category", "Target Weight %"])
        fig_donut = px.pie(df_alloc, values="Target Weight %", names="Category", hole=0.5, title="Target Portfolio Weights")
        fig_donut.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_donut, use_container_width=True)

else:
    st.info("No matching schemes found for selected filters. Try lowering minimum star rating.")
