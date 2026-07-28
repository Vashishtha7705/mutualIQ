"""
Unit test suite for Module 5 SQL Query Bank & Business Reporting.
"""

from pathlib import Path
import pandas as pd
import pytest

from src.database.db_manager import DatabaseManager
from src.database.loader import DatabaseLoader
from src.database.models import DimAMC, DimCategory, DimDate, DimInvestor, DimScheme, FactBenchmarkIndex, FactDailyNAV, FactTransaction
from src.database.query_bank import QueryBank


@pytest.fixture
def populated_db_manager(tmp_path):
    """Provides a populated test database for QueryBank unit testing."""
    db_file = tmp_path / "test_query_bank.db"
    mgr = DatabaseManager(f"sqlite:///{db_file}", force_new=True)
    mgr.create_tables()

    loader = DatabaseLoader(mgr)
    loader.seed_date_dimension("2026-07-20", "2026-07-24")

    with mgr.get_session() as session:
        amc = DimAMC(fund_house_name="HDFC Mutual Fund")
        cat = DimCategory(category_name="Equity - Large Cap", asset_class="Equity")
        session.add_all([amc, cat])
        session.flush()

        scheme = DimScheme(
            scheme_code=119551,
            scheme_name="Mirae Asset Large Cap Fund",
            amc_id=amc.amc_id,
            category_id=cat.category_id
        )
        investor = DimInvestor(
            investor_name="Test Investor",
            email="test.investor@example.com",
            risk_profile="Aggressive",
            city="Mumbai"
        )
        session.add_all([scheme, investor])
        session.flush()

        # Add FactDailyNAV rows
        nav1 = FactDailyNAV(scheme_code=119551, date_id=20260723, nav=100.0, daily_return=0.0, log_return=0.0, cumulative_return=0.0, rolling_30d_volatility=0.10)
        nav2 = FactDailyNAV(scheme_code=119551, date_id=20260724, nav=105.0, daily_return=0.05, log_return=0.048, cumulative_return=0.05, rolling_30d_volatility=0.12)
        
        # Add FactBenchmarkIndex rows
        b1 = FactBenchmarkIndex(index_name="NIFTY_50_TRI", date_id=20260723, close_value=18000.0, daily_return=0.0, log_return=0.0, cumulative_return=0.0)
        b2 = FactBenchmarkIndex(index_name="NIFTY_50_TRI", date_id=20260724, close_value=18180.0, daily_return=0.01, log_return=0.0099, cumulative_return=0.01)

        # Add FactTransaction
        txn = FactTransaction(investor_id=investor.investor_id, scheme_code=119551, date_id=20260723, txn_type="BUY_SIP", units=10.0, purchase_nav=100.0, total_amount=1000.0)

        session.add_all([nav1, nav2, b1, b2, txn])

    yield mgr


def test_get_top_performing_schemes(populated_db_manager):
    qb = QueryBank(populated_db_manager)
    df = qb.get_top_performing_schemes(top_n=5)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "scheme_name" in df.columns
    assert "cumulative_return_pct" in df.columns
    assert df.iloc[0]["scheme_code"] == 119551


def test_get_category_performance_summary(populated_db_manager):
    qb = QueryBank(populated_db_manager)
    df = qb.get_category_performance_summary()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "category_name" in df.columns
    assert df.iloc[0]["category_name"] == "Equity - Large Cap"


def test_get_scheme_vs_benchmark_comparison(populated_db_manager):
    qb = QueryBank(populated_db_manager)
    df = qb.get_scheme_vs_benchmark_comparison(scheme_code=119551, index_name="NIFTY_50_TRI")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "scheme_nav" in df.columns
    assert "benchmark_close" in df.columns
    assert "excess_daily_return_pct" in df.columns
    assert len(df) == 2


def test_get_investor_portfolio_summary(populated_db_manager):
    qb = QueryBank(populated_db_manager)
    df = qb.get_investor_portfolio_summary()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "investor_name" in df.columns
    assert "total_profit_loss" in df.columns
    # Total units = 10. Current NAV = 105. Current value = 1050. Invested = 1000. Profit = 50.
    assert df.iloc[0]["total_profit_loss"] == 50.0


def test_get_rolling_trend_analysis(populated_db_manager):
    qb = QueryBank(populated_db_manager)
    df = qb.get_rolling_trend_analysis(scheme_code=119551, window_days=30)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "rolling_moving_avg_nav" in df.columns
