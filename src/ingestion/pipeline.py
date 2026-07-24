"""
Data Ingestion Pipeline Orchestrator.
Coordinates extraction of daily AMFI NAV feeds, target scheme historical time-series,
and benchmark index data into the raw data landing zone.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.ingestion.amfi_ingestor import AMFIIngestor
from src.ingestion.mfapi_ingestor import MFAPIIngestor
from src.ingestion.benchmark_ingestor import BenchmarkIngestor
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Sample representative mutual fund scheme codes across categories for analytical depth
DEFAULT_TARGET_SCHEMES = [
    "119551",  # Mirae Asset Large Cap Fund - Growth
    "120503",  # Axis Small Cap Fund - Growth
    "100027",  # SBI Bluechip Fund - Growth
    "118989",  # HDFC Mid-Cap Opportunities Fund - Growth
    "120505",  # Parag Parikh Flexi Cap Fund - Growth
    "100377",  # ICICI Prudential Equity & Debt Fund - Growth
]


class IngestionPipeline:
    """
    Orchestration master for Module 2 Data Ingestion tasks.
    """

    def __init__(self, target_scheme_codes: Optional[List[str]] = None):
        self.target_scheme_codes = target_scheme_codes or DEFAULT_TARGET_SCHEMES
        self.amfi_ingestor = AMFIIngestor()
        self.mfapi_ingestor = MFAPIIngestor()
        self.benchmark_ingestor = BenchmarkIngestor()

    def run(self) -> Dict[str, Any]:
        """
        Executes complete ingestion pipeline workflow.
        
        Returns:
            Dict[str, Any]: Summary metrics of the ingestion run.
        """
        start_time = datetime.now()
        logger.info("==================================================")
        logger.info("  STARTING DATA INGESTION PIPELINE (MODULE 2)    ")
        logger.info("==================================================")

        summary: Dict[str, Any] = {
            "start_time": start_time.isoformat(),
            "amfi_records_count": 0,
            "schemes_ingested_count": 0,
            "benchmarks_ingested_count": 0,
            "status": "SUCCESS",
            "errors": []
        }

        # Step 1: Ingest Daily AMFI NAV Feed
        try:
            logger.info("--- Phase 1: Ingesting AMFI Bulk Daily Feed ---")
            raw_text = self.amfi_ingestor.fetch_raw_nav_feed()
            self.amfi_ingestor.save_raw_feed(raw_text)
            records = self.amfi_ingestor.parse_raw_feed(raw_text)
            summary["amfi_records_count"] = len(records)
        except Exception as exc:
            logger.error("Phase 1 AMFI ingestion error: %s", exc)
            summary["errors"].append(f"AMFI: {str(exc)}")

        # Step 2: Ingest Target Schemes Historical Data from MFAPI
        try:
            logger.info("--- Phase 2: Ingesting Historical Scheme NAVs ---")
            mfapi_results = self.mfapi_ingestor.batch_fetch_schemes(self.target_scheme_codes)
            summary["schemes_ingested_count"] = len(mfapi_results)
        except Exception as exc:
            logger.error("Phase 2 MFAPI ingestion error: %s", exc)
            summary["errors"].append(f"MFAPI: {str(exc)}")

        # Step 3: Ingest Historical Benchmark Indices
        try:
            logger.info("--- Phase 3: Ingesting Benchmark Indices ---")
            benchmark_paths = self.benchmark_ingestor.run_default_benchmarks()
            summary["benchmarks_ingested_count"] = len(benchmark_paths)
        except Exception as exc:
            logger.error("Phase 3 Benchmark ingestion error: %s", exc)
            summary["errors"].append(f"Benchmark: {str(exc)}")

        end_time = datetime.now()
        duration_sec = (end_time - start_time).total_seconds()
        summary["end_time"] = end_time.isoformat()
        summary["duration_seconds"] = round(duration_sec, 2)

        if summary["errors"]:
            summary["status"] = "COMPLETED_WITH_ERRORS"

        logger.info("==================================================")
        logger.info("  INGESTION PIPELINE COMPLETED IN %.2f SECONDS   ", duration_sec)
        logger.info("  AMFI Records: %d | Schemes: %d | Benchmarks: %d", 
                    summary["amfi_records_count"], summary["schemes_ingested_count"], summary["benchmarks_ingested_count"])
        logger.info("==================================================")

        return summary


if __name__ == "__main__":
    pipeline = IngestionPipeline()
    pipeline.run()
