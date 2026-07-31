"""
Multi-Factor Mutual Fund Scoring Engine.
Applies category-peer min-max normalization and weighted multi-factor scoring
to assign composite scores (0-100) and 1 to 5 Star Ratings.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from src.analytics.metrics_engine import MetricsEngine
from src.database.db_manager import DatabaseManager, get_db_manager
from src.database.query_bank import QueryBank
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FundScorer:
    """
    Quantitative Multi-Factor Fund Scorer.
    """

    DEFAULT_WEIGHTS = {
        "returns": 0.30,           # 30% Weight: CAGR & Cumulative Returns
        "risk_adjusted": 0.25,     # 25% Weight: Sharpe & Sortino Ratios
        "downside_protection": 0.20, # 20% Weight: Max Drawdown & Calmar Ratio
        "alpha": 0.15,             # 15% Weight: Alpha & Information Ratio
        "volatility": 0.10,        # 10% Weight: Annualized Volatility & Tracking Error
    }

    def __init__(self, db_manager: Optional[DatabaseManager] = None, weights: Optional[Dict[str, float]] = None):
        self.db_mgr = db_manager or get_db_manager()
        self.metrics_engine = MetricsEngine()
        self.weights = weights or self.DEFAULT_WEIGHTS

    def fetch_all_schemes_raw_metrics(self) -> pd.DataFrame:
        """
        Calculates raw quantitative metrics for all schemes stored in the database.
        """
        sql = """
        SELECT 
            s.scheme_code,
            s.scheme_name,
            c.category_name,
            a.fund_house_name
        FROM dim_scheme s
        JOIN dim_category c ON s.category_id = c.category_id
        JOIN dim_amc a ON s.amc_id = a.amc_id;
        """

        with self.db_mgr.get_session() as session:
            df_schemes = pd.read_sql(sql, session.bind)

        if df_schemes.empty:
            return pd.DataFrame()

        # Fetch benchmark index series
        sql_bench = "SELECT full_date AS date, daily_return FROM fact_benchmark_index b JOIN dim_date d ON b.date_id = d.date_id WHERE b.index_name = 'NIFTY_50_TRI' ORDER BY date ASC;"
        with self.db_mgr.get_session() as session:
            df_bench = pd.read_sql(sql_bench, session.bind)

        records = []
        logger.info("Computing raw quantitative metrics for %d schemes...", len(df_schemes))

        for _, row in df_schemes.iterrows():
            scheme_code = int(row["scheme_code"])
            sql_nav = "SELECT full_date AS date, nav, daily_return FROM fact_daily_nav f JOIN dim_date d ON f.date_id = d.date_id WHERE f.scheme_code = :code ORDER BY date ASC;"
            with self.db_mgr.get_session() as session:
                df_nav = pd.read_sql(sql_nav, session.bind, params={"code": scheme_code})

            if df_nav.empty:
                continue

            metrics = self.metrics_engine.compute_full_scheme_metrics(df_nav, df_bench)
            if not metrics:
                continue

            metrics["scheme_code"] = scheme_code
            metrics["scheme_name"] = str(row["scheme_name"])
            metrics["category_name"] = str(row["category_name"])
            metrics["fund_house_name"] = str(row["fund_house_name"])
            records.append(metrics)

        df_raw = pd.DataFrame(records)
        logger.info("Successfully calculated raw metrics for %d schemes", len(df_raw))
        return df_raw

    @staticmethod
    def _min_max_scale(series: pd.Series, invert: bool = False) -> pd.Series:
        """
        Normalizes a pandas series into 0-100 range.
        If invert=True, lower values get higher scores (for risk/volatility).
        """
        min_val = series.min()
        max_val = series.max()

        if max_val == min_val:
            return pd.Series(50.0, index=series.index)

        if invert:
            scaled = ((max_val - series) / (max_val - min_val)) * 100.0
        else:
            scaled = ((series - min_val) / (max_val - min_val)) * 100.0

        return scaled

    def score_and_rank_schemes(self, df_raw: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Normalizes raw metrics within category peer groups, computes weighted composite score (0-100),
        and assigns 1-Star to 5-Star Ratings.
        """
        if df_raw is None or df_raw.empty:
            df_raw = self.fetch_all_schemes_raw_metrics()

        if df_raw.empty:
            return pd.DataFrame()

        df = df_raw.copy()
        scored_dfs = []

        # Process per Category peer group
        for category, group in df.groupby("category_name"):
            g = group.copy()

            # 1. Component Dimension Scores (0 - 100 scale)
            returns_score = (
                self._min_max_scale(g["cagr_pct"]) * 0.7 +
                self._min_max_scale(g["absolute_return_pct"]) * 0.3
            )
            risk_adj_score = (
                self._min_max_scale(g["sharpe_ratio"]) * 0.5 +
                self._min_max_scale(g["sortino_ratio"]) * 0.5
            )
            downside_score = (
                self._min_max_scale(g["max_drawdown_pct"].abs(), invert=True) * 0.6 +
                self._min_max_scale(g["calmar_ratio"]) * 0.4
            )
            alpha_score = (
                self._min_max_scale(g["alpha_pct"]) * 0.6 +
                self._min_max_scale(g["information_ratio"]) * 0.4
            )
            volatility_score = (
                self._min_max_scale(g["annualized_volatility_pct"], invert=True) * 0.6 +
                self._min_max_scale(g["tracking_error_pct"], invert=True) * 0.4
            )

            # 2. Weighted Composite Score
            w = self.weights
            composite_score = (
                returns_score * w["returns"] +
                risk_adj_score * w["risk_adjusted"] +
                downside_score * w["downside_protection"] +
                alpha_score * w["alpha"] +
                volatility_score * w["volatility"]
            )

            g["composite_score"] = composite_score.round(2)
            g["category_rank"] = g["composite_score"].rank(ascending=False, method="min").astype(int)

            # 3. Star Rating Allocation based on Percentiles
            pct_rank = g["composite_score"].rank(pct=True)
            g["star_rating"] = np.select(
                [
                    pct_rank >= 0.85,
                    pct_rank >= 0.65,
                    pct_rank >= 0.35,
                    pct_rank >= 0.15,
                ],
                [5, 4, 3, 2],
                default=1
            )
            g["rating_label"] = g["star_rating"].map({
                5: "⭐⭐⭐⭐⭐ Excellent",
                4: "⭐⭐⭐⭐ Above Average",
                3: "⭐⭐⭐ Average",
                2: "⭐⭐ Below Average",
                1: "⭐ Poor",
            })

            scored_dfs.append(g)

        df_final = pd.concat(scored_dfs, ignore_index=True)
        df_final = df_final.sort_values(by=["category_name", "category_rank"]).reset_index(drop=True)
        logger.info("Successfully scored and ranked %d schemes across categories", len(df_final))
        return df_final
