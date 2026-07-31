"""
Fund Scoring & Recommendation Engine Package.
Provides multi-factor quantitative fund scoring, category peer normalization,
star-rating classification, and personalized investor recommendations.
"""

from src.scoring.fund_scorer import FundScorer
from src.scoring.recommendation import RecommendationEngine

__all__ = [
    "FundScorer",
    "RecommendationEngine",
]
