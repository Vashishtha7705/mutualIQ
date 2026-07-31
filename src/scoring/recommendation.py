"""
Automated Mutual Fund Recommendation Engine.
Matches investor risk profiles with top-rated schemes and constructs model portfolio allocations.
"""

from typing import Dict, List, Optional, Any
import pandas as pd

from src.scoring.fund_scorer import FundScorer
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RecommendationEngine:
    """
    Personalized Mutual Fund Recommendation Engine.
    """

    RISK_PROFILE_MAPPINGS = {
        "Aggressive": {
            "categories": ["Equity - Small Cap", "Equity - Mid Cap", "Equity - Flexi Cap", "Equity - Large Cap"],
            "model_allocation": {
                "Equity - Small Cap": 30,
                "Equity - Mid Cap": 30,
                "Equity - Flexi Cap": 25,
                "Equity - Large Cap": 15,
            },
        },
        "Moderate": {
            "categories": ["Equity - Large Cap", "Equity - Flexi Cap", "Hybrid - Aggressive Hybrid"],
            "model_allocation": {
                "Equity - Large Cap": 40,
                "Equity - Flexi Cap": 35,
                "Hybrid - Aggressive Hybrid": 25,
            },
        },
        "Conservative": {
            "categories": ["Debt - Fixed Income", "Hybrid - Arbitrage", "Other - Index / ETF"],
            "model_allocation": {
                "Debt - Fixed Income": 50,
                "Hybrid - Arbitrage": 30,
                "Other - Index / ETF": 20,
            },
        },
    }

    def __init__(self, fund_scorer: Optional[FundScorer] = None):
        self.scorer = fund_scorer or FundScorer()

    def get_recommendations_for_profile(
        self,
        risk_profile: str = "Aggressive",
        min_star_rating: int = 4,
        top_n_per_category: int = 2
    ) -> Dict[str, Any]:
        """
        Generates top mutual fund recommendations and model portfolio allocation tailored to investor risk profile.
        """
        profile_config = self.RISK_PROFILE_MAPPINGS.get(risk_profile, self.RISK_PROFILE_MAPPINGS["Moderate"])
        allowed_categories = profile_config["categories"]
        model_alloc = profile_config["model_allocation"]

        logger.info("Generating fund recommendations for '%s' Risk Profile...", risk_profile)

        # 1. Fetch scored and ranked schemes
        df_scored = self.scorer.score_and_rank_schemes()

        if df_scored.empty:
            return {}

        # 2. Filter by allowed categories and minimum star rating
        df_filtered = df_scored[
            (df_scored["category_name"].isin(allowed_categories)) &
            (df_scored["star_rating"] >= min_star_rating)
        ].copy()

        # Fallback if no 4/5 star funds exist in target categories
        if df_filtered.empty:
            df_filtered = df_scored[df_scored["category_name"].isin(allowed_categories)].copy()

        # 3. Select top N schemes per category
        recommended_schemes = []
        for cat, group in df_filtered.groupby("category_name"):
            top_group = group.sort_values(by="category_rank").head(top_n_per_category)
            for _, row in top_group.iterrows():
                recommended_schemes.append({
                    "scheme_code": int(row["scheme_code"]),
                    "scheme_name": str(row["scheme_name"]),
                    "category_name": str(row["category_name"]),
                    "fund_house_name": str(row["fund_house_name"]),
                    "star_rating": int(row["star_rating"]),
                    "rating_label": str(row["rating_label"]),
                    "composite_score": float(row["composite_score"]),
                    "cagr_pct": float(row["cagr_pct"]),
                    "sharpe_ratio": float(row["sharpe_ratio"]),
                    "max_drawdown_pct": float(row["max_drawdown_pct"]),
                    "suggested_category_weight_pct": model_alloc.get(str(row["category_name"]), 20),
                })

        logger.info("Recommended %d top-rated schemes for '%s' profile", len(recommended_schemes), risk_profile)

        return {
            "risk_profile": risk_profile,
            "min_star_rating": min_star_rating,
            "target_categories": allowed_categories,
            "recommended_schemes": recommended_schemes,
            "model_portfolio_allocation": model_alloc,
        }
