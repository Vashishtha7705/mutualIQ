"""
Quantitative Financial Metrics Engine.
Vectorized mathematical implementation of risk, return, and benchmark performance ratios.
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from src.config.config_loader import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MetricsEngine:
    """
    Quantitative Risk & Performance Analytics Calculator.
    """

    def __init__(self, risk_free_rate: Optional[float] = None, trading_days: int = 252):
        config = get_config()
        self.risk_free_rate = (
            risk_free_rate if risk_free_rate is not None else config.get("financial_defaults.risk_free_rate", 0.065)
        )
        self.trading_days = trading_days

    @staticmethod
    def calculate_cagr(nav_series: pd.Series, dates: pd.Series) -> float:
        """
        Calculates Compound Annual Growth Rate (CAGR).
        CAGR = (NAV_end / NAV_start) ** (365 / N_days) - 1
        """
        if len(nav_series) < 2:
            return 0.0

        nav_start = float(nav_series.iloc[0])
        nav_end = float(nav_series.iloc[-1])

        if nav_start <= 0 or nav_end <= 0:
            return 0.0

        dt_start = pd.to_datetime(dates.iloc[0])
        dt_end = pd.to_datetime(dates.iloc[-1])
        n_days = (dt_end - dt_start).days

        if n_days <= 0:
            return 0.0

        cagr = ((nav_end / nav_start) ** (365.0 / n_days)) - 1.0
        return float(cagr)

    def calculate_annualized_volatility(self, daily_returns: pd.Series) -> float:
        """
        Calculates annualized volatility: std(R_daily) * sqrt(252).
        """
        if len(daily_returns) < 2:
            return 0.0
        vol = daily_returns.std() * np.sqrt(self.trading_days)
        return float(vol)

    def calculate_downside_volatility(self, daily_returns: pd.Series) -> float:
        """
        Calculates downside volatility (standard deviation of negative returns).
        """
        neg_returns = daily_returns[daily_returns < 0]
        if len(neg_returns) < 2:
            return 0.0
        downside_vol = neg_returns.std() * np.sqrt(self.trading_days)
        return float(downside_vol)

    def calculate_sharpe_ratio(self, cagr: float, annualized_volatility: float) -> float:
        """
        Calculates Sharpe Ratio: (CAGR - Rf) / Volatility.
        """
        if annualized_volatility <= 0:
            return 0.0
        return float((cagr - self.risk_free_rate) / annualized_volatility)

    def calculate_sortino_ratio(self, cagr: float, downside_volatility: float) -> float:
        """
        Calculates Sortino Ratio: (CAGR - Rf) / Downside_Volatility.
        """
        if downside_volatility <= 0:
            return 0.0
        return float((cagr - self.risk_free_rate) / downside_volatility)

    @staticmethod
    def calculate_max_drawdown(nav_series: pd.Series) -> Tuple[float, pd.Series]:
        """
        Calculates Maximum Drawdown (MDD) and drawdown time series.
        MDD = min((NAV_t - Peak_t) / Peak_t)
        Returns: (mdd_value, drawdown_series)
        """
        if len(nav_series) == 0:
            return 0.0, pd.Series()

        running_max = nav_series.cummax()
        drawdown = (nav_series - running_max) / running_max
        max_dd = float(drawdown.min())
        return max_dd, drawdown

    def calculate_calmar_ratio(self, cagr: float, max_drawdown: float) -> float:
        """
        Calculates Calmar Ratio: CAGR / abs(Max_Drawdown).
        """
        abs_mdd = abs(max_drawdown)
        if abs_mdd <= 0:
            return 0.0
        return float(cagr / abs_mdd)

    @staticmethod
    def calculate_beta_and_alpha(
        scheme_returns: pd.Series,
        benchmark_returns: pd.Series,
        risk_free_rate: float = 0.065,
        trading_days: int = 252
    ) -> Tuple[float, float]:
        """
        Calculates Beta (covariance / variance) and Jensen's Alpha.
        Beta = Cov(Rp, Rm) / Var(Rm)
        Alpha = CAGR_p - [Rf + Beta * (CAGR_m - Rf)]
        """
        if len(scheme_returns) != len(benchmark_returns) or len(scheme_returns) < 5:
            return 1.0, 0.0

        cov_matrix = np.cov(scheme_returns, benchmark_returns)
        var_bm = cov_matrix[1, 1]

        if var_bm <= 0:
            beta = 1.0
        else:
            beta = cov_matrix[0, 1] / var_bm

        # Annualized CAGR approximations for Alpha
        cagr_p = ((1 + scheme_returns.mean()) ** trading_days) - 1.0
        cagr_m = ((1 + benchmark_returns.mean()) ** trading_days) - 1.0

        alpha = cagr_p - (risk_free_rate + beta * (cagr_m - risk_free_rate))
        return float(beta), float(alpha)

    def calculate_treynor_ratio(self, cagr: float, beta: float) -> float:
        """
        Calculates Treynor Ratio: (CAGR - Rf) / Beta.
        """
        if abs(beta) <= 1e-6:
            return 0.0
        return float((cagr - self.risk_free_rate) / beta)

    def calculate_tracking_error_and_information_ratio(
        self,
        scheme_returns: pd.Series,
        benchmark_returns: pd.Series,
        trading_days: int = 252
    ) -> Tuple[float, float]:
        """
        Calculates Tracking Error and Information Ratio.
        Tracking Error = std(Rp - Rm) * sqrt(252)
        Information Ratio = (CAGR_p - CAGR_m) / Tracking_Error
        """
        if len(scheme_returns) != len(benchmark_returns) or len(scheme_returns) < 5:
            return 0.0, 0.0

        diff_returns = scheme_returns - benchmark_returns
        tracking_error = float(diff_returns.std() * np.sqrt(trading_days))

        cagr_p = ((1 + scheme_returns.mean()) ** trading_days) - 1.0
        cagr_m = ((1 + benchmark_returns.mean()) ** trading_days) - 1.0

        if tracking_error <= 0:
            info_ratio = 0.0
        else:
            info_ratio = float((cagr_p - cagr_m) / tracking_error)

        return tracking_error, info_ratio

    @staticmethod
    def calculate_var_and_cvar(
        daily_returns: pd.Series, confidence_level: float = 0.95
    ) -> Tuple[float, float]:
        """
        Calculates Historical Value at Risk (VaR) and Conditional VaR (CVaR / Expected Shortfall).
        Returns: (VaR_daily_pct, CVaR_daily_pct)
        """
        if len(daily_returns) < 10:
            return 0.0, 0.0

        cutoff_percentile = (1.0 - confidence_level) * 100.0
        var_val = float(np.percentile(daily_returns, cutoff_percentile))

        # CVaR is average return of tail losses beyond VaR
        tail_returns = daily_returns[daily_returns <= var_val]
        if len(tail_returns) == 0:
            cvar_val = var_val
        else:
            cvar_val = float(tail_returns.mean())

        return abs(var_val), abs(cvar_val)

    def compute_full_scheme_metrics(
        self,
        df_scheme_nav: pd.DataFrame,
        df_benchmark_nav: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Computes a comprehensive dictionary of all quantitative metrics for a given scheme time series.
        """
        if df_scheme_nav.empty or "nav" not in df_scheme_nav.columns:
            return {}

        df = df_scheme_nav.sort_values(by="date").reset_index(drop=True)
        nav_series = df["nav"]
        dates = df["date"]

        if "daily_return" in df.columns:
            daily_returns = df["daily_return"]
        else:
            daily_returns = nav_series.pct_change().fillna(0.0)

        # Core Return & Risk calculations
        abs_return = float((nav_series.iloc[-1] / nav_series.iloc[0]) - 1.0) if nav_series.iloc[0] > 0 else 0.0
        cagr = self.calculate_cagr(nav_series, dates)
        ann_vol = self.calculate_annualized_volatility(daily_returns)
        downside_vol = self.calculate_downside_volatility(daily_returns)
        max_dd, _ = self.calculate_max_drawdown(nav_series)

        # Risk-Adjusted Ratios
        sharpe = self.calculate_sharpe_ratio(cagr, ann_vol)
        sortino = self.calculate_sortino_ratio(cagr, downside_vol)
        calmar = self.calculate_calmar_ratio(cagr, max_dd)

        # VaR & CVaR (95%)
        var_95, cvar_95 = self.calculate_var_and_cvar(daily_returns, confidence_level=0.95)

        # Benchmark Relative Ratios (if benchmark provided)
        beta, alpha, treynor, tracking_error, info_ratio = 1.0, 0.0, 0.0, 0.0, 0.0
        if df_benchmark_nav is not None and not df_benchmark_nav.empty:
            # Align dates
            df_merged = pd.merge(
                df[["date", "daily_return"]],
                df_benchmark_nav[["date", "daily_return"]],
                on="date",
                suffixes=("_p", "_m")
            ).dropna()

            if len(df_merged) >= 5:
                beta, alpha = self.calculate_beta_and_alpha(
                    df_merged["daily_return_p"], df_merged["daily_return_m"], self.risk_free_rate, self.trading_days
                )
                treynor = self.calculate_treynor_ratio(cagr, beta)
                tracking_error, info_ratio = self.calculate_tracking_error_and_information_ratio(
                    df_merged["daily_return_p"], df_merged["daily_return_m"], self.trading_days
                )

        return {
            "start_date": str(dates.iloc[0]),
            "end_date": str(dates.iloc[-1]),
            "total_trading_days": len(df),
            "latest_nav": float(nav_series.iloc[-1]),
            "absolute_return_pct": round(abs_return * 100, 2),
            "cagr_pct": round(cagr * 100, 2),
            "annualized_volatility_pct": round(ann_vol * 100, 2),
            "downside_volatility_pct": round(downside_vol * 100, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "calmar_ratio": round(calmar, 2),
            "beta": round(beta, 2),
            "alpha_pct": round(alpha * 100, 2),
            "treynor_ratio": round(treynor, 4),
            "tracking_error_pct": round(tracking_error * 100, 2),
            "information_ratio": round(info_ratio, 2),
            "var_95_daily_pct": round(var_95 * 100, 2),
            "cvar_95_daily_pct": round(cvar_95 * 100, 2),
        }
