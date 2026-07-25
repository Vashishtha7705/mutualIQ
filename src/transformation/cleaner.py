"""
Data Cleaning & Normalization Module.
Parses multi-format dates, standardizes AMC categories, removes duplicates,
and filters out invalid NAV/Index records.
"""

from datetime import datetime
import re
from typing import Any, Dict, List, Tuple
import pandas as pd

from src.transformation.schemas import SchemeMetaSchema, DailyNAVSchema, BenchmarkSchema
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataCleaner:
    """
    Data Cleaning Engine for raw Mutual Fund datasets.
    """

    CATEGORY_MAPPINGS = {
        r".*Large Cap.*": "Equity - Large Cap",
        r".*Mid Cap.*": "Equity - Mid Cap",
        r".*Small Cap.*": "Equity - Small Cap",
        r".*Flexi Cap.*": "Equity - Flexi Cap",
        r".*Multi Cap.*": "Equity - Multi Cap",
        r".*ELSS.*": "Equity - ELSS (Tax Saving)",
        r".*Focused.*": "Equity - Focused",
        r".*Value.*": "Equity - Value / Contra",
        r".*Sectoral.*|.*Thematic.*": "Equity - Sectoral / Thematic",
        r".*Equity & Debt.*|.*Hybrid.*|.*Balanced.*": "Hybrid - Aggressive Hybrid",
        r".*Arbitrage.*": "Hybrid - Arbitrage",
        r".*Debt.*|.*Bond.*|.*Gilt.*|.*Liquid.*": "Debt - Fixed Income",
        r".*Index.*|.*ETF.*": "Other - Index / ETF",
    }

    @staticmethod
    def parse_date(date_str: str) -> str:
        """
        Parses date string across common financial formats into ISO 'YYYY-MM-DD'.
        Supports: '24-Jul-2026', '24-07-2026', '2026-07-24', '2026/07/24'.
        """
        if not date_str or not isinstance(date_str, str):
            raise ValueError(f"Invalid date format: {date_str}")

        date_str = date_str.strip()
        formats = [
            "%d-%b-%Y",  # 24-Jul-2026
            "%d-%m-%Y",  # 24-07-2026
            "%Y-%m-%d",  # 2026-07-24
            "%d/%m/%Y",  # 24/07/2026
            "%Y/%m/%d",  # 2026/07/24
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        raise ValueError(f"Unable to parse date string '{date_str}' with known formats")

    @classmethod
    def standardize_category(cls, raw_category: str) -> str:
        """
        Normalizes long AMFI category strings into standard benchmark categories.
        Example: 'Open Ended Schemes ( Equity Scheme - Large Cap Fund )' -> 'Equity - Large Cap'
        """
        if not raw_category:
            return "Equity - Other"

        for pattern, standard_name in cls.CATEGORY_MAPPINGS.items():
            if re.search(pattern, raw_category, re.IGNORECASE):
                return standard_name

        return "Other - General"

    @classmethod
    def clean_fund_house(cls, raw_fund_house: str) -> str:
        """
        Normalizes Fund House (AMC) names by stripping unnecessary text.
        """
        if not raw_fund_house or raw_fund_house == "Unknown":
            return "Unknown AMC"

        cleaned = raw_fund_house.strip()
        cleaned = re.sub(r"^Mutual Fund Name:\s*", "", cleaned, flags=re.IGNORECASE)
        return cleaned

    def clean_amfi_scheme_metadata(self, raw_records: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Cleans raw AMFI bulk records and extracts validated Scheme Metadata DataFrame.
        """
        logger.info("Cleaning %d raw AMFI records for scheme metadata extraction...", len(raw_records))
        valid_schemes: Dict[int, Dict[str, Any]] = {}

        for rec in raw_records:
            try:
                code_int = int(rec["scheme_code"])
                if code_int <= 0:
                    continue

                category_std = self.standardize_category(rec.get("category", ""))
                fund_house_std = self.clean_fund_house(rec.get("fund_house", ""))

                # Validate schema with Pydantic
                validated = SchemeMetaSchema(
                    scheme_code=code_int,
                    scheme_name=rec.get("scheme_name", ""),
                    category=category_std,
                    fund_house=fund_house_std,
                    isin_payout=rec.get("isin_payout"),
                    isin_reinvest=rec.get("isin_reinvest"),
                )

                # Keep latest occurrence per scheme_code
                valid_schemes[validated.scheme_code] = validated.model_dump()
            except Exception:
                continue

        df = pd.DataFrame(list(valid_schemes.values()))
        if not df.empty:
            df = df.sort_values(by="scheme_code").reset_index(drop=True)
        logger.info("Successfully extracted %d clean, unique Scheme Metadata records", len(df))
        return df

    def clean_daily_nav_series(self, scheme_code: int, raw_nav_list: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Cleans and validates historical daily NAV series for a single scheme code.
        """
        valid_rows: List[Dict[str, Any]] = []

        for item in raw_nav_list:
            try:
                date_iso = self.parse_date(item.get("date", ""))
                nav_float = float(item.get("nav", 0.0))

                if nav_float <= 0:
                    continue

                dt_obj = datetime.strptime(date_iso, "%Y-%m-%d").date()
                validated = DailyNAVSchema(
                    scheme_code=scheme_code,
                    date=dt_obj,
                    nav=nav_float
                )
                valid_rows.append({
                    "scheme_code": validated.scheme_code,
                    "date": validated.date.strftime("%Y-%m-%d"),
                    "nav": validated.nav
                })
            except Exception:
                continue

        df = pd.DataFrame(valid_rows)
        if df.empty:
            logger.warning("No valid NAV records found for scheme %d", scheme_code)
            return pd.DataFrame(columns=["scheme_code", "date", "nav"])

        # Deduplicate on (scheme_code, date) keeping first, sort chronologically
        df = df.drop_duplicates(subset=["scheme_code", "date"]).sort_values(by="date").reset_index(drop=True)
        return df

    def clean_benchmark_series(self, index_name: str, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans raw benchmark index DataFrame.
        """
        valid_rows: List[Dict[str, Any]] = []

        for _, row in df_raw.iterrows():
            try:
                date_iso = self.parse_date(str(row["date"]))
                close_val = float(row["close_value"])

                if close_val <= 0:
                    continue

                dt_obj = datetime.strptime(date_iso, "%Y-%m-%d").date()
                validated = BenchmarkSchema(
                    index_name=index_name,
                    date=dt_obj,
                    close_value=close_val
                )
                valid_rows.append({
                    "index_name": validated.index_name,
                    "date": validated.date.strftime("%Y-%m-%d"),
                    "close_value": validated.close_value
                })
            except Exception:
                continue

        df = pd.DataFrame(valid_rows)
        if not df.empty:
            df = df.drop_duplicates(subset=["index_name", "date"]).sort_values(by="date").reset_index(drop=True)
        return df
