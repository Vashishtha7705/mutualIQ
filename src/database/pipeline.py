"""
Database Pipeline Orchestrator.
Initializes Star-Schema database tables, seeds dimensions, and populates fact tables.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import pandas as pd

from src.config.config_loader import get_config
from src.database.db_manager import DatabaseManager, get_db_manager
from src.database.loader import DatabaseLoader
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabasePipeline:
    """
    Orchestration master for Module 4 Database tasks.
    """

    def __init__(self, db_url: str = None):
        self.db_mgr = get_db_manager(db_url)
        self.loader = DatabaseLoader(self.db_mgr)
        config = get_config()
        self.processed_dir = Path(config.get("paths.processed_data_dir", "data/processed"))

    def run(self) -> Dict[str, Any]:
        """
        Executes full database DDL table creation and ETL loading workflow.
        """
        start_time = datetime.now()
        logger.info("==================================================")
        logger.info("   STARTING DATABASE PIPELINE (MODULE 4)         ")
        logger.info("==================================================")

        summary: Dict[str, Any] = {
            "start_time": start_time.isoformat(),
            "date_records": 0,
            "scheme_records": 0,
            "investor_records": 0,
            "daily_nav_records": 0,
            "benchmark_records": 0,
            "transaction_records": 0,
            "status": "SUCCESS",
            "errors": []
        }

        # Step 1: Create Tables
        try:
            self.db_mgr.create_tables()
        except Exception as exc:
            logger.error("Database DDL creation failed: %s", exc)
            summary["errors"].append(f"DDL: {str(exc)}")

        # Step 2: Seed Date Dimension
        try:
            summary["date_records"] = self.loader.seed_date_dimension()
        except Exception as exc:
            logger.error("Date dimension seeding failed: %s", exc)
            summary["errors"].append(f"DimDate: {str(exc)}")

        # Step 3: Load Metadata & Schemes
        meta_csv = self.processed_dir / "clean_scheme_metadata.csv"
        if meta_csv.exists():
            try:
                df_meta = pd.read_csv(meta_csv)
                amc_map, cat_map = self.loader.load_amc_and_category_dimensions(df_meta)
                summary["scheme_records"] = self.loader.load_scheme_dimension(df_meta, amc_map, cat_map)
            except Exception as exc:
                logger.error("Scheme dimension loading failed: %s", exc)
                summary["errors"].append(f"DimScheme: {str(exc)}")
        else:
            logger.warning("Processed metadata file %s not found.", meta_csv)

        # Step 4: Seed Investors
        try:
            summary["investor_records"] = self.loader.seed_investor_dimension()
        except Exception as exc:
            logger.error("Investor dimension seeding failed: %s", exc)
            summary["errors"].append(f"DimInvestor: {str(exc)}")

        # Step 5: Load Fact Daily NAV
        nav_parquet = self.processed_dir / "clean_daily_nav.parquet"
        if nav_parquet.exists():
            try:
                df_nav = pd.read_parquet(nav_parquet)
                summary["daily_nav_records"] = self.loader.load_fact_daily_nav(df_nav)
            except Exception as exc:
                logger.error("Fact daily NAV loading failed: %s", exc)
                summary["errors"].append(f"FactDailyNAV: {str(exc)}")
        else:
            logger.warning("Processed daily NAV parquet file %s not found.", nav_parquet)

        # Step 6: Load Fact Benchmark Index
        bench_parquet = self.processed_dir / "clean_benchmarks.parquet"
        if bench_parquet.exists():
            try:
                df_bench = pd.read_parquet(bench_parquet)
                summary["benchmark_records"] = self.loader.load_fact_benchmark_index(df_bench)
            except Exception as exc:
                logger.error("Fact benchmark index loading failed: %s", exc)
                summary["errors"].append(f"FactBenchmark: {str(exc)}")
        else:
            logger.warning("Processed benchmark parquet file %s not found.", bench_parquet)

        # Step 7: Generate Fact Transactions
        try:
            summary["transaction_records"] = self.loader.generate_fact_transactions()
        except Exception as exc:
            logger.error("Fact transactions loading failed: %s", exc)
            summary["errors"].append(f"FactTransactions: {str(exc)}")

        end_time = datetime.now()
        duration_sec = (end_time - start_time).total_seconds()
        summary["end_time"] = end_time.isoformat()
        summary["duration_seconds"] = round(duration_sec, 2)

        if summary["errors"]:
            summary["status"] = "COMPLETED_WITH_ERRORS"

        logger.info("==================================================")
        logger.info(" DATABASE PIPELINE COMPLETED IN %.2f SECONDS     ", duration_sec)
        logger.info(" Dates: %d | Schemes: %d | Daily NAVs: %d | Benchmarks: %d | Txns: %d",
                    summary["date_records"], summary["scheme_records"], summary["daily_nav_records"],
                    summary["benchmark_records"], summary["transaction_records"])
        logger.info("==================================================")

        return summary


if __name__ == "__main__":
    pipeline = DatabasePipeline()
    pipeline.run()
