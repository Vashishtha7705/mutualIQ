"""
Unit test suite for Module 4 Database Layer & Star Schema.
"""

from pathlib import Path
import pytest
from sqlalchemy import select, func

from src.database.db_manager import DatabaseManager
from src.database.models import (
    Base,
    DimAMC,
    DimCategory,
    DimDate,
    DimInvestor,
    DimScheme,
    FactBenchmarkIndex,
    FactDailyNAV,
    FactTransaction,
)
from src.database.loader import DatabaseLoader
from src.database.pipeline import DatabasePipeline


@pytest.fixture
def in_memory_db_manager(tmp_path):
    """Provides an isolated SQLite database file for testing."""
    db_file = tmp_path / "test_mutual_funds.db"
    db_url = f"sqlite:///{db_file}"
    mgr = DatabaseManager(db_url)
    mgr.create_tables()
    yield mgr


def test_database_table_creation(in_memory_db_manager):
    mgr = in_memory_db_manager
    with mgr.get_session() as session:
        # Verify DDL tables exist by querying counts
        amc_count = session.query(func.count(DimAMC.amc_id)).scalar()
        assert amc_count == 0


def test_seed_date_dimension(in_memory_db_manager):
    loader = DatabaseLoader(in_memory_db_manager)
    count = loader.seed_date_dimension(start_date="2024-01-01", end_date="2024-01-10")
    assert count == 10

    with in_memory_db_manager.get_session() as session:
        first_date = session.query(DimDate).filter_by(date_id=20240101).first()
        assert first_date is not None
        assert first_date.year == 2024
        assert first_date.month == 1
        assert first_date.month_name == "January"


def test_star_schema_loading_and_joins(in_memory_db_manager):
    mgr = in_memory_db_manager
    loader = DatabaseLoader(mgr)

    # 1. Seed date dimension
    loader.seed_date_dimension(start_date="2026-07-20", end_date="2026-07-24")

    # 2. Add AMC, Category, and Scheme
    with mgr.get_session() as session:
        amc = DimAMC(fund_house_name="SBI Mutual Fund")
        cat = DimCategory(category_name="Equity - Large Cap", asset_class="Equity")
        session.add_all([amc, cat])
        session.flush()

        scheme = DimScheme(
            scheme_code=100027,
            scheme_name="SBI Bluechip Fund",
            amc_id=amc.amc_id,
            category_id=cat.category_id
        )
        session.add(scheme)

    # 3. Insert FactDailyNAV
    with mgr.get_session() as session:
        fact_nav = FactDailyNAV(
            scheme_code=100027,
            date_id=20260724,
            nav=75.43,
            daily_return=0.015,
            log_return=0.0148,
            cumulative_return=0.25,
            rolling_30d_volatility=0.12
        )
        session.add(fact_nav)

    # 4. Execute Dimensional Star-Schema JOIN Query
    with mgr.get_session() as session:
        stmt = (
            select(
                DimScheme.scheme_name,
                DimAMC.fund_house_name,
                DimCategory.category_name,
                DimDate.full_date,
                FactDailyNAV.nav,
                FactDailyNAV.daily_return
            )
            .join(DimScheme, FactDailyNAV.scheme_code == DimScheme.scheme_code)
            .join(DimAMC, DimScheme.amc_id == DimAMC.amc_id)
            .join(DimCategory, DimScheme.category_id == DimCategory.category_id)
            .join(DimDate, FactDailyNAV.date_id == DimDate.date_id)
            .where(FactDailyNAV.scheme_code == 100027)
        )

        result = session.execute(stmt).first()
        assert result is not None
        assert result.scheme_name == "SBI Bluechip Fund"
        assert result.fund_house_name == "SBI Mutual Fund"
        assert result.category_name == "Equity - Large Cap"
        assert result.nav == 75.43
        assert result.daily_return == 0.015
