"""
Power BI Integration & Data Export Module.
Exports Star-Schema relational tables into optimized CSV files under data/processed/powerbi/
for direct drag-and-drop import into Power BI Desktop.
"""

from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from src.config.config_loader import get_config
from src.database.db_manager import DatabaseManager, get_db_manager
from src.scoring.fund_scorer import FundScorer
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PowerBIExporter:
    """
    Export pipeline generating Power BI ready Star-Schema CSV data files.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_mgr = db_manager or get_db_manager()
        config = get_config()
        self.export_dir = Path(config.get("paths.processed_data_dir", "data/processed")) / "powerbi"
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_all_tables(self) -> Dict[str, Path]:
        """
        Exports all Dimension and Fact tables from SQLite database into CSV files in data/processed/powerbi/.
        """
        logger.info("==================================================")
        logger.info("   STARTING POWER BI DATA EXPORT PIPELINE        ")
        logger.info("==================================================")

        tables = [
            "dim_amc",
            "dim_category",
            "dim_scheme",
            "dim_date",
            "dim_investor",
            "fact_daily_nav",
            "fact_benchmark_index",
            "fact_transactions",
        ]

        exported_files: Dict[str, Path] = {}

        with self.db_mgr.get_session() as session:
            for table_name in tables:
                try:
                    sql = f"SELECT * FROM {table_name}"
                    df = pd.read_sql(sql, session.bind)
                    out_path = self.export_dir / f"{table_name}.csv"
                    df.to_csv(out_path, index=False)
                    exported_files[table_name] = out_path
                    logger.info("Exported Power BI table '%s' (%d rows) -> %s", table_name, len(df), out_path)
                except Exception as exc:
                    logger.error("Failed to export table '%s': %s", table_name, exc)

        # Export Scored Summary Matrix
        try:
            scorer = FundScorer(self.db_mgr)
            df_scored = scorer.score_and_rank_schemes()
            if not df_scored.empty:
                out_scored = self.export_dir / "fund_scores_summary.csv"
                df_scored.to_csv(out_scored, index=False)
                exported_files["fund_scores_summary"] = out_scored
                logger.info("Exported Fund Scores Summary (%d rows) -> %s", len(df_scored), out_scored)
        except Exception as exc:
            logger.error("Failed to export Fund Scores Summary: %s", exc)

        logger.info("==================================================")
        logger.info("   POWER BI EXPORT COMPLETED: %d FILES CREATED    ", len(exported_files))
        logger.info("==================================================")

        return exported_files


if __name__ == "__main__":
    exporter = PowerBIExporter()
    exporter.export_all_tables()
