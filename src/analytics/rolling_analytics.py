"""
Rolling Financial Analytics Engine.
Calculates 1-Year, 3-Year, and 5-Year rolling CAGR, rolling volatility,
rolling Sharpe ratios, and peak-to-trough drawdown time series.
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from src.config.config_loader import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RollingAnalyticsEngine:
    """
    Rolling Performance & Risk Time-Series Generator.
    """

    def __init__(self, risk_free_rate: Optional[float] = None, trading_days_per_year: int = 252):
        config = get_config()
        self.risk_free_rate = (
            risk_free_rate if risk_free_rate is not None else config.get("financial_defaults.risk_free_rate", 0.065)
        )
        self.trading_days = trading_days_per_year

    def compute_rolling_returns(
        self,
        df_nav: pd.DataFrame,
        window_years: List[int] = [1, 3, 5]
    ) -> pd.DataFrame:
        """
        Computes rolling CAGR time series for 1-Year (252 days), 3-Year (756 days), and 5-Year (1260 days).
        
        Formula for k-year rolling CAGR at index t:
        CAGR_t = (NAV_t / NAV_{t - k*252}) ** (1 / k) - 1
        """
        if df_nav.empty or "nav" not in df_nav.columns:
            return pd.DataFrame()

        df = df_nav.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(by="date").reset_index(drop=True)

        for yrs in window_years:
            days = yrs * self.trading_days
            col_name = f"rolling_{yrs}y_cagr"
            
            nav_shift = df["nav"].shift(days)
            rolling_cagr = np.where(
                (nav_shift > 0) & (df["nav"] > 0),
                ((df["nav"] / nav_shift) ** (1.0 / yrs)) - 1.0,
                np.nan
            )
            df[col_name] = rolling_cagr

        return df

    def compute_rolling_sharpe_ratio(
        self,
        df_nav: pd.DataFrame,
        window_days: int = 252
    ) -> pd.DataFrame:
        """
        Computes rolling 1-Year annualized Sharpe Ratio time-series.
        """
        if df_nav.empty or "nav" not in df_nav.columns:
            return pd.DataFrame()

        df = df_nav.copy()
        if "daily_return" not in df.columns:
            df["daily_return"] = df["nav"].pct_change().fillna(0.0)

        rolling_mean_ret = df["daily_return"].rolling(window=window_days, min_periods=30).mean() * self.trading_days
        rolling_std_ret = df["daily_return"].rolling(window=window_days, min_periods=30).std() * np.sqrt(self.trading_days)

        df["rolling_1y_sharpe"] = np.where(
            rolling_std_ret > 0,
            (rolling_mean_ret - self.risk_free_rate) / rolling_std_ret,
            np.nan
        )

        return df

    @staticmethod
    def compute_drawdown_series(df_nav: pd.DataFrame) -> pd.DataFrame:
        """
        Computes peak-to-trough drawdown series.
        """
        if df_nav.empty or "nav" not in df_nav.columns:
            return pd.DataFrame()

        df = df_nav.copy()
        df["running_peak"] = df["nav"].cummax()
        df["drawdown"] = (df["nav"] - df["running_peak"]) / df["running_peak"]
        df["drawdown_pct"] = df["drawdown"] * 100.0
        return df
