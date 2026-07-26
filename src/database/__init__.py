"""
Database Package
Provides SQLAlchemy models, Database Connection Manager, Star Schema DDL definitions,
and ETL Database Loaders.
"""

from src.database.db_manager import DatabaseManager, get_db_manager
from src.database.models import (
    Base,
    DimAMC,
    DimCategory,
    DimScheme,
    DimDate,
    DimInvestor,
    FactDailyNAV,
    FactBenchmarkIndex,
    FactTransaction,
)
from src.database.loader import DatabaseLoader
from src.database.pipeline import DatabasePipeline

__all__ = [
    "DatabaseManager",
    "get_db_manager",
    "Base",
    "DimAMC",
    "DimCategory",
    "DimScheme",
    "DimDate",
    "DimInvestor",
    "FactDailyNAV",
    "FactBenchmarkIndex",
    "FactTransaction",
    "DatabaseLoader",
    "DatabasePipeline",
]
