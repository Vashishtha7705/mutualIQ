"""
Unit test suite for Module 7 Investor Analytics & XIRR Engine.
"""

from datetime import date
import pandas as pd
import pytest

from src.analytics.portfolio import xirr, PortfolioTracker
from src.database.db_manager import DatabaseManager
from src.database.loader import DatabaseLoader
from src.database.models import DimAMC, DimCategory, DimDate, DimInvestor, DimScheme, FactDailyNAV, FactTransaction


def test_xirr_exact_one_year_15_percent():
    # Outflow Rs 100,000 on 2024-01-01, Inflow Rs 115,000 on 2025-01-01 (1 year = 15.0% return)
    cashflows = [
        (date(2024, 1, 1), -100000.0),
        (date(2025, 1, 1), 115000.0),
    ]

    rate = xirr(cashflows)
    # Expected rate: 0.150 (15.0%)
    assert pytest.approx(rate, abs=1e-3) == 0.150


def test_xirr_monthly_sip():
    # Monthly SIP of Rs 10,000 for 3 months, ending value Rs 31,500
    cashflows = [
        (date(2024, 1, 1), -10000.0),
        (date(2024, 2, 1), -10000.0),
        (date(2024, 3, 1), -10000.0),
        (date(2024, 4, 1), 31500.0),
    ]

    rate = xirr(cashflows)
    assert rate > 0.0
    assert rate < 1.0


def test_xirr_invalid_cashflows():
    # Only negative cashflows
    assert xirr([(date(2024, 1, 1), -100.0)]) == 0.0
    # Empty cashflows
    assert xirr([]) == 0.0


@pytest.fixture
def populated_portfolio_db(tmp_path):
    db_file = tmp_path / "test_portfolio.db"
    mgr = DatabaseManager(f"sqlite:///{db_file}", force_new=True)
    mgr.create_tables()

    loader = DatabaseLoader(mgr)
    loader.seed_date_dimension("2024-01-01", "2025-01-01")

    investor_id = None
    with mgr.get_session() as session:
        amc = DimAMC(fund_house_name="Axis Mutual Fund")
        cat = DimCategory(category_name="Equity - Small Cap", asset_class="Equity")
        session.add_all([amc, cat])
        session.flush()

        scheme = DimScheme(
            scheme_code=120503,
            scheme_name="Axis Small Cap Fund",
            amc_id=amc.amc_id,
            category_id=cat.category_id
        )
        investor = DimInvestor(
            investor_name="Priya Patel",
            email="priya@example.com",
            risk_profile="Aggressive",
            city="Bengaluru"
        )
        session.add_all([scheme, investor])
        session.flush()
        investor_id = investor.investor_id

        # Add FactDailyNAV
        nav1 = FactDailyNAV(scheme_code=120503, date_id=20240101, nav=100.0, daily_return=0.0)
        nav2 = FactDailyNAV(scheme_code=120503, date_id=20250101, nav=120.0, daily_return=0.20)

        # Add FactTransaction: Invest 10,000 on 2024-01-01 (100 units at NAV 100)
        txn = FactTransaction(
            investor_id=investor_id,
            scheme_code=120503,
            date_id=20240101,
            txn_type="BUY_SIP",
            units=100.0,
            purchase_nav=100.0,
            total_amount=10000.0
        )
        session.add_all([nav1, nav2, txn])

    yield mgr, investor_id


def test_portfolio_tracker(populated_portfolio_db):
    mgr, investor_id = populated_portfolio_db
    tracker = PortfolioTracker(mgr)

    report = tracker.get_portfolio_summary_report(investor_id)

    assert report["investor_name"] == "Priya Patel"
    assert report["total_invested_amount"] == 10000.0
    # 100 units * 120 NAV = 12000
    assert report["total_current_value"] == 12000.0
    assert report["total_pnl"] == 2000.0
    assert report["total_return_pct"] == 20.0
    assert report["xirr_pct"] > 0.0
    assert len(report["holdings"]) == 1
    assert len(report["asset_allocation"]) == 1
