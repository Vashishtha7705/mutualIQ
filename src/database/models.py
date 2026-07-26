"""
SQLAlchemy 2.0 ORM Models for Star-Schema Analytical Database.
Defines Dimension and Fact tables with indexes, foreign key relationships,
and composite unique constraints.
"""

from datetime import date
from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""
    pass


class DimAMC(Base):
    """
    Dimension Table: Asset Management Company (AMC / Fund House).
    """
    __tablename__ = "dim_amc"

    amc_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fund_house_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    schemes: Mapped[List["DimScheme"]] = relationship("DimScheme", back_populates="amc")


class DimCategory(Base):
    """
    Dimension Table: Mutual Fund Category & Asset Class.
    """
    __tablename__ = "dim_category"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    asset_class: Mapped[str] = mapped_column(String(50), nullable=False, default="Equity")

    schemes: Mapped[List["DimScheme"]] = relationship("DimScheme", back_populates="category")


class DimScheme(Base):
    """
    Dimension Table: Mutual Fund Scheme Master Details.
    """
    __tablename__ = "dim_scheme"

    scheme_code: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    scheme_name: Mapped[str] = mapped_column(String(255), nullable=False)
    amc_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_amc.amc_id"), nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_category.category_id"), nullable=False)
    isin_payout: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    isin_reinvest: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    amc: Mapped["DimAMC"] = relationship("DimAMC", back_populates="schemes")
    category: Mapped["DimCategory"] = relationship("DimCategory", back_populates="schemes")
    daily_navs: Mapped[List["FactDailyNAV"]] = relationship("FactDailyNAV", back_populates="scheme")
    transactions: Mapped[List["FactTransaction"]] = relationship("FactTransaction", back_populates="scheme")


class DimDate(Base):
    """
    Dimension Table: Calendar & Fiscal Date Master.
    date_id is stored in integer format YYYYMMDD (e.g., 20260724).
    """
    __tablename__ = "dim_date"

    date_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # YYYYMMDD
    full_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    month_name: Mapped[str] = mapped_column(String(20), nullable=False)
    day_of_month: Mapped[int] = mapped_column(Integer, nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    day_name: Mapped[str] = mapped_column(String(20), nullable=False)
    is_weekend: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    daily_navs: Mapped[List["FactDailyNAV"]] = relationship("FactDailyNAV", back_populates="date_dim")
    benchmarks: Mapped[List["FactBenchmarkIndex"]] = relationship("FactBenchmarkIndex", back_populates="date_dim")
    transactions: Mapped[List["FactTransaction"]] = relationship("FactTransaction", back_populates="date_dim")


class DimInvestor(Base):
    """
    Dimension Table: Investor Demographics & Portfolio Profile.
    """
    __tablename__ = "dim_investor"

    investor_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investor_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    risk_profile: Mapped[str] = mapped_column(String(50), nullable=False, default="Moderate")
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Mumbai")

    transactions: Mapped[List["FactTransaction"]] = relationship("FactTransaction", back_populates="investor")


class FactDailyNAV(Base):
    """
    Fact Table: Daily Scheme Net Asset Values (NAV) & Quantitative Returns.
    """
    __tablename__ = "fact_daily_nav"

    nav_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scheme_code: Mapped[int] = mapped_column(Integer, ForeignKey("dim_scheme.scheme_code"), nullable=False)
    date_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_date.date_id"), nullable=False)
    nav: Mapped[float] = mapped_column(Float, nullable=False)
    daily_return: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    log_return: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cumulative_return: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rolling_30d_volatility: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    scheme: Mapped["DimScheme"] = relationship("DimScheme", back_populates="daily_navs")
    date_dim: Mapped["DimDate"] = relationship("DimDate", back_populates="daily_navs")

    __table_args__ = (
        UniqueConstraint("scheme_code", "date_id", name="uq_scheme_date"),
        Index("idx_fact_nav_scheme_date", "scheme_code", "date_id"),
        Index("idx_fact_nav_date", "date_id"),
    )


class FactBenchmarkIndex(Base):
    """
    Fact Table: Benchmark Index Historical Daily Closing Prices & Returns.
    """
    __tablename__ = "fact_benchmark_index"

    benchmark_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    index_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_date.date_id"), nullable=False)
    close_value: Mapped[float] = mapped_column(Float, nullable=False)
    daily_return: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    log_return: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cumulative_return: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    date_dim: Mapped["DimDate"] = relationship("DimDate", back_populates="benchmarks")

    __table_args__ = (
        UniqueConstraint("index_name", "date_id", name="uq_index_date"),
        Index("idx_fact_bench_index_date", "index_name", "date_id"),
    )


class FactTransaction(Base):
    """
    Fact Table: Investor Mutual Fund Buy/Sell/SIP Transactions.
    """
    __tablename__ = "fact_transactions"

    txn_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investor_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_investor.investor_id"), nullable=False)
    scheme_code: Mapped[int] = mapped_column(Integer, ForeignKey("dim_scheme.scheme_code"), nullable=False)
    date_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_date.date_id"), nullable=False)
    txn_type: Mapped[str] = mapped_column(String(20), nullable=False)  # BUY_SIP, BUY_LUMPSUM, SELL_REDEMPTION
    units: Mapped[float] = mapped_column(Float, nullable=False)
    purchase_nav: Mapped[float] = mapped_column(Float, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)

    investor: Mapped["DimInvestor"] = relationship("DimInvestor", back_populates="transactions")
    scheme: Mapped["DimScheme"] = relationship("DimScheme", back_populates="transactions")
    date_dim: Mapped["DimDate"] = relationship("DimDate", back_populates="transactions")

    __table_args__ = (
        Index("idx_fact_txn_investor_scheme", "investor_id", "scheme_code"),
        Index("idx_fact_txn_date", "date_id"),
    )
