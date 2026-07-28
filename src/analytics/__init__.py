"""
Quantitative Financial Analytics Package
Provides vectorized calculation engines for returns (CAGR, Rolling Returns),
risk metrics (Volatility, Downside Deviation, Max Drawdown, VaR, CVaR),
and benchmark risk-adjusted ratios (Sharpe, Sortino, Beta, Alpha, Treynor, Tracking Error, Information Ratio).
"""

from src.analytics.metrics_engine import MetricsEngine
from src.analytics.rolling_analytics import RollingAnalyticsEngine

__all__ = [
    "MetricsEngine",
    "RollingAnalyticsEngine",
]
