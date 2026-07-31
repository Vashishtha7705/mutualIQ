"""
Unit test suite for Module 8 Fund Scoring & Recommendation Engine.
"""

from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest

from src.scoring.fund_scorer import FundScorer
from src.scoring.recommendation import RecommendationEngine


def test_min_max_scale():
    series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    scaled = FundScorer._min_max_scale(series)
    assert scaled.min() == 0.0
    assert scaled.max() == 100.0
    assert pytest.approx(scaled.iloc[2], abs=1e-4) == 50.0

    # Inverted scaling (lower values get higher scores)
    inverted = FundScorer._min_max_scale(series, invert=True)
    assert inverted.iloc[0] == 100.0  # lowest input 10 gets 100
    assert inverted.iloc[-1] == 0.0   # highest input 50 gets 0


def test_score_and_rank_schemes():
    scorer = FundScorer()

    raw_metrics = pd.DataFrame([
        {
            "scheme_code": 1,
            "scheme_name": "Fund Alpha",
            "category_name": "Equity - Large Cap",
            "fund_house_name": "AMC One",
            "cagr_pct": 20.0,
            "absolute_return_pct": 50.0,
            "sharpe_ratio": 1.5,
            "sortino_ratio": 2.0,
            "max_drawdown_pct": -10.0,
            "calmar_ratio": 2.0,
            "alpha_pct": 3.0,
            "information_ratio": 1.2,
            "annualized_volatility_pct": 12.0,
            "tracking_error_pct": 3.0,
        },
        {
            "scheme_code": 2,
            "scheme_name": "Fund Beta",
            "category_name": "Equity - Large Cap",
            "fund_house_name": "AMC Two",
            "cagr_pct": 10.0,
            "absolute_return_pct": 25.0,
            "sharpe_ratio": 0.5,
            "sortino_ratio": 0.8,
            "max_drawdown_pct": -25.0,
            "calmar_ratio": 0.4,
            "alpha_pct": -1.0,
            "information_ratio": -0.2,
            "annualized_volatility_pct": 20.0,
            "tracking_error_pct": 6.0,
        },
    ])

    df_scored = scorer.score_and_rank_schemes(raw_metrics)

    assert not df_scored.empty
    assert "composite_score" in df_scored.columns
    assert "star_rating" in df_scored.columns
    assert "category_rank" in df_scored.columns

    # Fund Alpha should rank 1st with higher score
    alpha_row = df_scored[df_scored["scheme_code"] == 1].iloc[0]
    beta_row = df_scored[df_scored["scheme_code"] == 2].iloc[0]

    assert alpha_row["composite_score"] > beta_row["composite_score"]
    assert alpha_row["category_rank"] == 1
    assert beta_row["category_rank"] == 2


def test_recommendation_engine():
    rec_engine = RecommendationEngine()

    raw_metrics = pd.DataFrame([
        {
            "scheme_code": 101,
            "scheme_name": "Small Cap Star",
            "category_name": "Equity - Small Cap",
            "fund_house_name": "Star AMC",
            "cagr_pct": 25.0,
            "absolute_return_pct": 80.0,
            "sharpe_ratio": 1.8,
            "sortino_ratio": 2.2,
            "max_drawdown_pct": -15.0,
            "calmar_ratio": 1.6,
            "alpha_pct": 5.0,
            "information_ratio": 1.5,
            "annualized_volatility_pct": 16.0,
            "tracking_error_pct": 4.0,
        },
        {
            "scheme_code": 102,
            "scheme_name": "Large Cap Steady",
            "category_name": "Equity - Large Cap",
            "fund_house_name": "Steady AMC",
            "cagr_pct": 14.0,
            "absolute_return_pct": 40.0,
            "sharpe_ratio": 1.2,
            "sortino_ratio": 1.5,
            "max_drawdown_pct": -8.0,
            "calmar_ratio": 1.75,
            "alpha_pct": 2.0,
            "information_ratio": 0.8,
            "annualized_volatility_pct": 10.0,
            "tracking_error_pct": 2.5,
        },
    ])

    df_scored = rec_engine.scorer.score_and_rank_schemes(raw_metrics)

    with patch.object(rec_engine.scorer, "score_and_rank_schemes", return_value=df_scored):
        res_agg = rec_engine.get_recommendations_for_profile("Aggressive", min_star_rating=1)
        assert res_agg["risk_profile"] == "Aggressive"
        assert len(res_agg["recommended_schemes"]) > 0

        res_mod = rec_engine.get_recommendations_for_profile("Moderate", min_star_rating=1)
        assert res_mod["risk_profile"] == "Moderate"
