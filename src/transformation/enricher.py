"""
Data Enrichment & Time Series Returns Module.
Calculates continuous calendar daily returns, log returns, cumulative returns,
and rolling metrics (volatility, rolling returns).
"""

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataEnricher:
    """
    Enriches time series datasets with quantitative financial metrics.
    """

    @staticmethod
    def enrich_daily_nav_returns(df_nav: pd.DataFrame) -> pd.DataFrame:
        """
        Enriches a clean daily NAV DataFrame for a single scheme with continuous calendar dates,
        forward-filled NAVs (handling non-trading days/weekends), and daily returns metrics.
        
        Input columns required: ['scheme_code', 'date', 'nav']
        Output columns added: ['daily_return', 'log_return', 'cumulative_return', 'rolling_30d_volatility']
        """
        if df_nav.empty:
            return pd.DataFrame(columns=["scheme_code", "date", "nav", "daily_return", "log_return", "cumulative_return"])

        df = df_nav.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(by="date").reset_index(drop=True)

        scheme_code = df["scheme_code"].iloc[0]

        # Resample to full continuous daily calendar range (to handle holiday gaps)
        date_idx = pd.date_range(start=df["date"].min(), end=df["date"].max(), freq="D")
        df_full = df.set_index("date").reindex(date_idx)
        df_full["scheme_code"] = scheme_code

        # Forward fill holiday NAV gaps, then backfill initial gap if any
        df_full["nav"] = df_full["nav"].ffill().bfill()

        # Simple Daily Return: R_t = (NAV_t - NAV_{t-1}) / NAV_{t-1}
        df_full["daily_return"] = df_full["nav"].pct_change().fillna(0.0)

        # Log Return: r_t = ln(NAV_t / NAV_{t-1})
        df_full["log_return"] = np.log(df_full["nav"] / df_full["nav"].shift(1)).fillna(0.0)

        # Cumulative Return: CR_t = (NAV_t / NAV_0) - 1
        first_nav = df_full["nav"].iloc[0]
        df_full["cumulative_return"] = (df_full["nav"] / first_nav) - 1.0

        # Rolling 30-day annualized volatility (30 calendar days ~ 21 trading days)
        df_full["rolling_30d_volatility"] = (
            df_full["daily_return"].rolling(window=30, min_periods=5).std() * np.sqrt(252)
        ).fillna(0.0)

        df_out = df_full.reset_index().rename(columns={"index": "date"})
        df_out["date"] = df_out["date"].dt.strftime("%Y-%m-%d")
        return df_out

    @staticmethod
    def enrich_benchmark_returns(df_bench: pd.DataFrame) -> pd.DataFrame:
        """
        Enriches benchmark index series with daily return and log return metrics.
        
        Input columns required: ['index_name', 'date', 'close_value']
        Output columns added: ['daily_return', 'log_return', 'cumulative_return']
        """
        if df_bench.empty:
            return pd.DataFrame(columns=["index_name", "date", "close_value", "daily_return", "log_return", "cumulative_return"])

        df = df_bench.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(by="date").reset_index(drop=True)

        index_name = df["index_name"].iloc[0]

        date_idx = pd.date_range(start=df["date"].min(), end=df["date"].max(), freq="D")
        df_full = df.set_index("date").reindex(date_idx)
        df_full["index_name"] = index_name
        df_full["close_value"] = df_full["close_value"].ffill().bfill()

        df_full["daily_return"] = df_full["close_value"].pct_change().fillna(0.0)
        df_full["log_return"] = np.log(df_full["close_value"] / df_full["close_value"].shift(1)).fillna(0.0)

        first_val = df_full["close_value"].iloc[0]
        df_full["cumulative_return"] = (df_full["close_value"] / first_val) - 1.0

        df_out = df_full.reset_index().rename(columns={"index": "date"})
        df_out["date"] = df_out["date"].dt.strftime("%Y-%m-%d")
        return df_out
