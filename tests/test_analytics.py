"""
Unit test suite for Module 6 Quantitative Financial Analytics Engine.
"""

import numpy as np
import pandas as pd
import pytest

from src.analytics.metrics_engine import MetricsEngine
from src.analytics.rolling_analytics import RollingAnalyticsEngine


def test_calculate_cagr():
    engine = MetricsEngine()

    # 100 to 200 over exactly 730 days (2 years: 2021-01-01 to 2023-01-01)
    dates = pd.Series(["2021-01-01", "2023-01-01"])
    navs = pd.Series([100.0, 200.0])

    cagr = engine.calculate_cagr(navs, dates)
    # (200/100)^(365/730) - 1 = sqrt(2) - 1 = 0.41421356...
    assert pytest.approx(cagr, abs=1e-4) == 0.41421356


def test_volatility_and_drawdown():
    engine = MetricsEngine()

    # 10 days of returns
    returns = pd.Series([0.01, -0.02, 0.015, -0.01, 0.02, -0.03, 0.01, 0.005, -0.015, 0.02])
    vol = engine.calculate_annualized_volatility(returns)
    downside_vol = engine.calculate_downside_volatility(returns)

    assert vol > 0
    assert downside_vol > 0
    assert downside_vol != vol

    navs = pd.Series([100.0, 110.0, 99.0, 105.0, 88.0, 95.0])
    max_dd, dd_series = engine.calculate_max_drawdown(navs)
    # Peak is 110. Minimum drops to 88. Drawdown = (88 - 110)/110 = -0.20 (-20%)
    assert pytest.approx(max_dd, abs=1e-4) == -0.20


def test_sharpe_sortino_calmar_ratios():
    engine = MetricsEngine(risk_free_rate=0.065)

    cagr = 0.15      # 15% CAGR
    vol = 0.10       # 10% Volatility
    downside_vol = 0.07  # 7% Downside Volatility
    max_dd = -0.10   # -10% Max Drawdown

    sharpe = engine.calculate_sharpe_ratio(cagr, vol)
    sortino = engine.calculate_sortino_ratio(cagr, downside_vol)
    calmar = engine.calculate_calmar_ratio(cagr, max_dd)

    # Sharpe = (0.15 - 0.065)/0.10 = 0.85
    assert pytest.approx(sharpe, abs=1e-4) == 0.85
    # Sortino = (0.15 - 0.065)/0.07 = 1.21428...
    assert pytest.approx(sortino, abs=1e-4) == 1.2142857
    # Calmar = 0.15 / 0.10 = 1.50
    assert pytest.approx(calmar, abs=1e-4) == 1.50


def test_beta_alpha_tracking_error():
    engine = MetricsEngine(risk_free_rate=0.065)

    # Generate benchmark returns
    np.random.seed(42)
    bm_returns = pd.Series(np.random.normal(0.0005, 0.01, 100))
    # Scheme returns with 1.2 Beta + noise
    scheme_returns = pd.Series(1.2 * bm_returns + np.random.normal(0.0001, 0.002, 100))

    beta, alpha = engine.calculate_beta_and_alpha(scheme_returns, bm_returns)
    te, ir = engine.calculate_tracking_error_and_information_ratio(scheme_returns, bm_returns)

    assert pytest.approx(beta, abs=0.1) == 1.2
    assert te > 0


def test_var_and_cvar():
    engine = MetricsEngine()

    returns = pd.Series(np.random.normal(0.0, 0.02, 1000))
    var_95, cvar_95 = engine.calculate_var_and_cvar(returns, confidence_level=0.95)

    assert var_95 > 0
    assert cvar_95 >= var_95


def test_full_scheme_metrics():
    engine = MetricsEngine()

    dates = [f"2024-01-{i:02d}" for i in range(1, 21)]
    navs = [100.0 + i * 0.5 + (1 if i % 2 == 0 else -1) for i in range(20)]
    df_scheme = pd.DataFrame({"date": dates, "nav": navs})
    df_scheme["daily_return"] = df_scheme["nav"].pct_change().fillna(0.0)

    metrics = engine.compute_full_scheme_metrics(df_scheme)

    assert "cagr_pct" in metrics
    assert "sharpe_ratio" in metrics
    assert "max_drawdown_pct" in metrics
    assert "var_95_daily_pct" in metrics


def test_rolling_analytics_engine():
    rolling_eng = RollingAnalyticsEngine()

    dates = pd.date_range("2020-01-01", periods=600, freq="B")
    navs = 100.0 * np.cumprod(1.0 + np.random.normal(0.0005, 0.01, 600))
    df_nav = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "nav": navs})

    # Rolling CAGR
    df_rolling = rolling_eng.compute_rolling_returns(df_nav, window_years=[1, 2])
    assert "rolling_1y_cagr" in df_rolling.columns

    # Rolling Sharpe
    df_sharpe = rolling_eng.compute_rolling_sharpe_ratio(df_nav, window_days=252)
    assert "rolling_1y_sharpe" in df_sharpe.columns

    # Drawdown Series
    df_dd = rolling_eng.compute_drawdown_series(df_nav)
    assert "drawdown_pct" in df_dd.columns
    assert df_dd["drawdown_pct"].min() <= 0
