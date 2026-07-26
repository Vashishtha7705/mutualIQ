"""
ETL Database Loader Module.
Reads clean Parquet/CSV datasets from data/processed landing zone,
seeds Dimension tables (Date, AMC, Category, Scheme, Investor),
and populates Fact tables (Daily NAV, Benchmark Index, Transactions).
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import pandas as pd
from sqlalchemy import insert, select, func

from src.config.config_loader import get_config
from src.database.db_manager import DatabaseManager, get_db_manager
from src.database.models import (
    DimAMC,
    DimCategory,
    DimDate,
    DimInvestor,
    DimScheme,
    FactBenchmarkIndex,
    FactDailyNAV,
    FactTransaction,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseLoader:
    """
    ETL Loader Engine for populating Star-Schema tables.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_mgr = db_manager or get_db_manager()
        config = get_config()
        self.processed_dir = Path(config.get("paths.processed_data_dir", "data/processed"))

    @staticmethod
    def date_to_date_id(dt: datetime) -> int:
        """Converts date/datetime object to integer YYYYMMDD format."""
        return dt.year * 10000 + dt.month * 100 + dt.day

    def seed_date_dimension(self, start_date: str = "2000-01-01", end_date: str = "2030-12-31") -> int:
        """
        Populates dim_date table with calendar metadata spanning 2000 to 2030.
        """
        with self.db_mgr.get_session() as session:
            count = session.query(func.count(DimDate.date_id)).scalar()
            if count and count > 4000:
                logger.info("dim_date already populated with %d records. Skipping seed.", count)
                return count

        logger.info("Seeding dim_date table from %s to %s...", start_date, end_date)
        dates = pd.date_range(start=start_date, end=end_date, freq="D")
        date_mappings: List[Dict] = []

        for dt in dates:
            d_id = self.date_to_date_id(dt)
            date_mappings.append({
                "date_id": d_id,
                "full_date": dt.date(),
                "year": dt.year,
                "quarter": dt.quarter,
                "month": dt.month,
                "month_name": dt.strftime("%B"),
                "day_of_month": dt.day,
                "day_of_week": dt.dayofweek + 1,  # 1=Monday, 7=Sunday
                "day_name": dt.strftime("%A"),
                "is_weekend": dt.dayofweek >= 5,
            })

        with self.db_mgr.get_session() as session:
            session.query(DimDate).delete()
            session.execute(insert(DimDate), date_mappings)

        logger.info("Successfully seeded %d calendar dates into dim_date", len(date_mappings))
        return len(date_mappings)

    def load_amc_and_category_dimensions(self, df_meta: pd.DataFrame) -> Tuple[Dict[str, int], Dict[str, int]]:
        """
        Extracts unique AMCs and Categories from metadata dataframe and populates dim_amc and dim_category.
        """
        logger.info("Populating dim_amc and dim_category dimensions...")
        amc_names = sorted([x for x in df_meta["fund_house"].unique() if x])
        category_names = sorted([x for x in df_meta["category"].unique() if x])

        amc_map: Dict[str, int] = {}
        category_map: Dict[str, int] = {}

        with self.db_mgr.get_session() as session:
            # Seed AMCs
            for name in amc_names:
                existing = session.query(DimAMC).filter_by(fund_house_name=name).first()
                if not existing:
                    amc_obj = DimAMC(fund_house_name=name)
                    session.add(amc_obj)
                    session.flush()
                    amc_map[name] = amc_obj.amc_id
                else:
                    amc_map[name] = existing.amc_id

            # Seed Categories
            for cat in category_names:
                asset_class = "Equity"
                if "Hybrid" in cat or "Arbitrage" in cat:
                    asset_class = "Hybrid"
                elif "Debt" in cat or "Fixed Income" in cat or "Bond" in cat:
                    asset_class = "Debt"
                elif "Index" in cat or "ETF" in cat:
                    asset_class = "Passive / Index"

                existing = session.query(DimCategory).filter_by(category_name=cat).first()
                if not existing:
                    cat_obj = DimCategory(category_name=cat, asset_class=asset_class)
                    session.add(cat_obj)
                    session.flush()
                    category_map[cat] = cat_obj.category_id
                else:
                    category_map[cat] = existing.category_id

        logger.info("Seeded %d AMCs and %d Categories", len(amc_map), len(category_map))
        return amc_map, category_map

    def load_scheme_dimension(self, df_meta: pd.DataFrame, amc_map: Dict[str, int], category_map: Dict[str, int]) -> int:
        """
        Populates dim_scheme table.
        """
        logger.info("Populating dim_scheme table (%d schemes)...", len(df_meta))
        scheme_records: List[Dict] = []

        for _, row in df_meta.iterrows():
            code = int(row["scheme_code"])
            amc_id = amc_map.get(row["fund_house"], 1)
            cat_id = category_map.get(row["category"], 1)

            scheme_records.append({
                "scheme_code": code,
                "scheme_name": str(row["scheme_name"]),
                "amc_id": amc_id,
                "category_id": cat_id,
                "isin_payout": str(row["isin_payout"]) if pd.notna(row["isin_payout"]) else None,
                "isin_reinvest": str(row["isin_reinvest"]) if pd.notna(row["isin_reinvest"]) else None,
            })

        with self.db_mgr.get_session() as session:
            for rec in scheme_records:
                session.merge(DimScheme(**rec))

        logger.info("Successfully populated dim_scheme dimension table")
        return len(scheme_records)

    def seed_investor_dimension(self) -> int:
        """
        Seeds dim_investor with sample investor profiles.
        """
        sample_investors = [
            {"investor_name": "Aarav Sharma", "email": "aarav.sharma@example.com", "risk_profile": "Aggressive", "city": "Mumbai"},
            {"investor_name": "Priya Patel", "email": "priya.patel@example.com", "risk_profile": "Moderate", "city": "Bengaluru"},
            {"investor_name": "Rohan Mehta", "email": "rohan.mehta@example.com", "risk_profile": "Conservative", "city": "Delhi"},
            {"investor_name": "Ananya Iyer", "email": "ananya.iyer@example.com", "risk_profile": "Aggressive", "city": "Chennai"},
            {"investor_name": "Vikram Singh", "email": "vikram.singh@example.com", "risk_profile": "Moderate", "city": "Hyderabad"},
        ]

        with self.db_mgr.get_session() as session:
            for inv in sample_investors:
                existing = session.query(DimInvestor).filter_by(email=inv["email"]).first()
                if not existing:
                    session.add(DimInvestor(**inv))

        logger.info("Seeded %d sample investor profiles into dim_investor", len(sample_investors))
        return len(sample_investors)

    def load_fact_daily_nav(self, df_nav: pd.DataFrame, chunk_size: int = 5000) -> int:
        """
        Populates fact_daily_nav table in optimized chunks, validating foreign keys against dim_scheme and dim_date.
        """
        logger.info("Populating fact_daily_nav table (%d rows)...", len(df_nav))

        df = df_nav.copy()
        df["date_dt"] = pd.to_datetime(df["date"])
        df["date_id"] = df["date_dt"].dt.year * 10000 + df["date_dt"].dt.month * 100 + df["date_dt"].dt.day

        # Get valid schemes and dates from DB to avoid FK violations
        with self.db_mgr.get_session() as session:
            valid_scheme_codes: Set[int] = set(r[0] for r in session.query(DimScheme.scheme_code).all())
            valid_date_ids: Set[int] = set(r[0] for r in session.query(DimDate.date_id).all())

        # If a scheme code present in NAV time series is not yet in dim_scheme, auto-register default
        missing_schemes = set(df["scheme_code"].unique()) - valid_scheme_codes
        if missing_schemes:
            logger.info("Auto-registering %d missing schemes in dim_scheme...", len(missing_schemes))
            with self.db_mgr.get_session() as session:
                for sc in missing_schemes:
                    session.merge(DimScheme(
                        scheme_code=int(sc),
                        scheme_name=f"Scheme {sc}",
                        amc_id=1,
                        category_id=1
                    ))
                valid_scheme_codes.update(missing_schemes)

        # Filter valid FKs
        df_valid = df[df["scheme_code"].isin(valid_scheme_codes) & df["date_id"].isin(valid_date_ids)]

        records = df_valid[[
            "scheme_code", "date_id", "nav", "daily_return", "log_return",
            "cumulative_return", "rolling_30d_volatility"
        ]].to_dict(orient="records")

        total_loaded = 0
        with self.db_mgr.get_session() as session:
            session.query(FactDailyNAV).delete()
            session.flush()

            for i in range(0, len(records), chunk_size):
                chunk = records[i:i + chunk_size]
                session.execute(insert(FactDailyNAV), chunk)
                total_loaded += len(chunk)
                logger.info("Loaded chunk %d/%d rows into fact_daily_nav", total_loaded, len(records))

        logger.info("Successfully populated %d rows into fact_daily_nav", total_loaded)
        return total_loaded

    def load_fact_benchmark_index(self, df_bench: pd.DataFrame) -> int:
        """
        Populates fact_benchmark_index table.
        """
        logger.info("Populating fact_benchmark_index table (%d rows)...", len(df_bench))

        df = df_bench.copy()
        df["date_dt"] = pd.to_datetime(df["date"])
        df["date_id"] = df["date_dt"].dt.year * 10000 + df["date_dt"].dt.month * 100 + df["date_dt"].dt.day

        with self.db_mgr.get_session() as session:
            valid_date_ids: Set[int] = set(r[0] for r in session.query(DimDate.date_id).all())

        df_valid = df[df["date_id"].isin(valid_date_ids)]

        records = df_valid[[
            "index_name", "date_id", "close_value", "daily_return", "log_return", "cumulative_return"
        ]].to_dict(orient="records")

        with self.db_mgr.get_session() as session:
            session.query(FactBenchmarkIndex).delete()
            session.execute(insert(FactBenchmarkIndex), records)

        logger.info("Successfully populated %d rows into fact_benchmark_index", len(records))
        return len(records)

    def generate_fact_transactions(self) -> int:
        """
        Generates realistic SIP & Lumpsum transactions for sample investors over past dates.
        """
        logger.info("Generating investor transactions into fact_transactions...")

        with self.db_mgr.get_session() as session:
            investor_ids = [inv.investor_id for inv in session.query(DimInvestor.investor_id).all()]
            schemes = session.query(DimScheme.scheme_code).all()

            if not investor_ids or not schemes:
                logger.warning("No investors or schemes found to generate transactions.")
                return 0

            target_scheme_codes = [s.scheme_code for s in schemes[:5]]

            session.query(FactTransaction).delete()
            txn_mappings: List[Dict] = []

            end_date = datetime.now()
            for inv_id in investor_ids:
                for scheme_code in target_scheme_codes:
                    sip_amount = 5000.0
                    for m in range(24, 0, -1):
                        dt = end_date - timedelta(days=m * 30)
                        dt_sip = datetime(dt.year, dt.month, 10)
                        date_id = self.date_to_date_id(dt_sip)

                        nav_record = session.query(FactDailyNAV.nav).filter_by(scheme_code=scheme_code, date_id=date_id).first()
                        nav_val = nav_record.nav if nav_record else 50.0

                        units = round(sip_amount / nav_val, 4)
                        txn_mappings.append({
                            "investor_id": inv_id,
                            "scheme_code": scheme_code,
                            "date_id": date_id,
                            "txn_type": "BUY_SIP",
                            "units": units,
                            "purchase_nav": nav_val,
                            "total_amount": sip_amount,
                        })

            session.execute(insert(FactTransaction), txn_mappings)

        logger.info("Successfully generated and loaded %d investor transactions into fact_transactions", len(txn_mappings))
        return len(txn_mappings)
