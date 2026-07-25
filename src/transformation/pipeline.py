"""
Data Transformation Pipeline Orchestrator.
Loads raw datasets from data/raw, cleans, validates schemas, enriches return metrics,
and writes optimized Parquet & CSV outputs to data/processed landing zone.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from src.config.config_loader import get_config
from src.ingestion.amfi_ingestor import AMFIIngestor
from src.transformation.cleaner import DataCleaner
from src.transformation.enricher import DataEnricher
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TransformationPipeline:
    """
    Orchestration master for Module 3 Data Transformation tasks.
    """

    def __init__(self):
        config = get_config()
        self.raw_dir = Path(config.get("paths.raw_data_dir", "data/raw"))
        self.processed_dir = Path(config.get("paths.processed_data_dir", "data/processed"))
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.cleaner = DataCleaner()
        self.enricher = DataEnricher()

    def process_scheme_metadata(self) -> pd.DataFrame:
        """
        Reads raw AMFI feed, extracts clean Scheme Metadata, and lands clean_scheme_metadata.csv.
        """
        amfi_raw_file = self.raw_dir / "amfi_nav_latest.txt"
        if not amfi_raw_file.exists():
            logger.warning("Raw AMFI file %s not found. Skipping scheme metadata cleaning.", amfi_raw_file)
            return pd.DataFrame()

        logger.info("Processing scheme metadata from raw feed: %s", amfi_raw_file)
        raw_text = amfi_raw_file.read_text(encoding="utf-8")
        amfi_ingestor = AMFIIngestor()
        raw_records = amfi_ingestor.parse_raw_feed(raw_text)

        df_meta = self.cleaner.clean_amfi_scheme_metadata(raw_records)
        out_csv = self.processed_dir / "clean_scheme_metadata.csv"
        df_meta.to_csv(out_csv, index=False)
        logger.info("Landed clean Scheme Metadata (%d rows) to %s", len(df_meta), out_csv)
        return df_meta

    def process_daily_nav_series(self) -> pd.DataFrame:
        """
        Reads all raw scheme_*.json files, validates daily NAVs, computes time-series returns,
        and lands consolidated clean_daily_nav.parquet & clean_daily_nav.csv.
        """
        json_files = list(self.raw_dir.glob("scheme_*.json"))
        if not json_files:
            logger.warning("No scheme raw JSON files found in %s", self.raw_dir)
            return pd.DataFrame()

        logger.info("Processing daily NAV series across %d scheme raw files...", len(json_files))
        all_scheme_dfs: List[pd.DataFrame] = []

        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    payload = json.load(f)

                meta = payload.get("meta", {})
                raw_data = payload.get("data", [])
                scheme_code = int(meta.get("scheme_code", 0))

                if scheme_code <= 0 or not raw_data:
                    continue

                # Step 1: Clean & validate raw list
                df_clean = self.cleaner.clean_daily_nav_series(scheme_code, raw_data)
                if df_clean.empty:
                    continue

                # Step 2: Enrich with calendar returns
                df_enriched = self.enricher.enrich_daily_nav_returns(df_clean)
                all_scheme_dfs.append(df_enriched)
            except Exception as exc:
                logger.error("Error processing raw file %s: %s", json_file.name, exc)

        if not all_scheme_dfs:
            logger.warning("No daily NAV records were processed.")
            return pd.DataFrame()

        df_consolidated = pd.concat(all_scheme_dfs, ignore_index=True)
        df_consolidated = df_consolidated.sort_values(by=["scheme_code", "date"]).reset_index(drop=True)

        # Write to Parquet & CSV
        out_parquet = self.processed_dir / "clean_daily_nav.parquet"
        out_csv = self.processed_dir / "clean_daily_nav.csv"
        df_consolidated.to_parquet(out_parquet, index=False)
        df_consolidated.to_csv(out_csv, index=False)

        logger.info("Landed clean consolidated Daily NAVs (%d rows) to %s", len(df_consolidated), out_parquet)
        return df_consolidated

    def process_benchmarks(self) -> pd.DataFrame:
        """
        Reads raw benchmark_*.csv files, cleans & enriches with return metrics,
        and lands consolidated clean_benchmarks.parquet & clean_benchmarks.csv.
        """
        csv_files = list(self.raw_dir.glob("benchmark_*.csv"))
        if not csv_files:
            logger.warning("No benchmark CSV files found in %s", self.raw_dir)
            return pd.DataFrame()

        logger.info("Processing benchmark indices across %d CSV files...", len(csv_files))
        all_bench_dfs: List[pd.DataFrame] = []

        for csv_file in csv_files:
            try:
                df_raw = pd.read_csv(csv_file)
                if df_raw.empty:
                    continue
                index_name = str(df_raw["index_name"].iloc[0])

                df_clean = self.cleaner.clean_benchmark_series(index_name, df_raw)
                if df_clean.empty:
                    continue

                df_enriched = self.enricher.enrich_benchmark_returns(df_clean)
                all_bench_dfs.append(df_enriched)
            except Exception as exc:
                logger.error("Error processing benchmark file %s: %s", csv_file.name, exc)

        if not all_bench_dfs:
            return pd.DataFrame()

        df_consolidated = pd.concat(all_bench_dfs, ignore_index=True)
        df_consolidated = df_consolidated.sort_values(by=["index_name", "date"]).reset_index(drop=True)

        out_parquet = self.processed_dir / "clean_benchmarks.parquet"
        out_csv = self.processed_dir / "clean_benchmarks.csv"
        df_consolidated.to_parquet(out_parquet, index=False)
        df_consolidated.to_csv(out_csv, index=False)

        logger.info("Landed clean consolidated Benchmarks (%d rows) to %s", len(df_consolidated), out_parquet)
        return df_consolidated

    def run(self) -> Dict[str, Any]:
        """
        Executes full transformation pipeline workflow.
        """
        start_time = datetime.now()
        logger.info("==================================================")
        logger.info(" STARTING DATA TRANSFORMATION PIPELINE (MODULE 3) ")
        logger.info("==================================================")

        summary: Dict[str, Any] = {
            "start_time": start_time.isoformat(),
            "metadata_rows": 0,
            "daily_nav_rows": 0,
            "benchmark_rows": 0,
            "status": "SUCCESS",
            "errors": []
        }

        try:
            df_meta = self.process_scheme_metadata()
            summary["metadata_rows"] = len(df_meta)
        except Exception as exc:
            logger.error("Error transforming scheme metadata: %s", exc)
            summary["errors"].append(f"Metadata: {str(exc)}")

        try:
            df_nav = self.process_daily_nav_series()
            summary["daily_nav_rows"] = len(df_nav)
        except Exception as exc:
            logger.error("Error transforming daily NAV series: %s", exc)
            summary["errors"].append(f"DailyNAV: {str(exc)}")

        try:
            df_bench = self.process_benchmarks()
            summary["benchmark_rows"] = len(df_bench)
        except Exception as exc:
            logger.error("Error transforming benchmark indices: %s", exc)
            summary["errors"].append(f"Benchmark: {str(exc)}")

        end_time = datetime.now()
        duration_sec = (end_time - start_time).total_seconds()
        summary["end_time"] = end_time.isoformat()
        summary["duration_seconds"] = round(duration_sec, 2)

        if summary["errors"]:
            summary["status"] = "COMPLETED_WITH_ERRORS"

        logger.info("==================================================")
        logger.info(" TRANSFORMATION PIPELINE FINISHED IN %.2f SECONDS ", duration_sec)
        logger.info(" Metadata: %d | Daily NAVs: %d | Benchmarks: %d",
                    summary["metadata_rows"], summary["daily_nav_rows"], summary["benchmark_rows"])
        logger.info("==================================================")

        return summary


if __name__ == "__main__":
    pipeline = TransformationPipeline()
    pipeline.run()
