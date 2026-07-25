"""
Unit test suite for Module 3 Data Cleaning, Validation & Transformation Layer.
"""

from datetime import date
from pathlib import Path
import pandas as pd
import pytest
from pydantic import ValidationError

from src.transformation.schemas import SchemeMetaSchema, DailyNAVSchema, BenchmarkSchema
from src.transformation.cleaner import DataCleaner
from src.transformation.enricher import DataEnricher
from src.transformation.pipeline import TransformationPipeline


def test_scheme_meta_schema_validation():
    # Valid model
    meta = SchemeMetaSchema(
        scheme_code=100027,
        scheme_name="SBI Bluechip Fund - Direct - Growth",
        category="Equity Scheme - Large Cap Fund",
        fund_house="SBI Mutual Fund"
    )
    assert meta.scheme_code == 100027

    # Invalid negative scheme code
    with pytest.raises(ValidationError):
        SchemeMetaSchema(
            scheme_code=-5,
            scheme_name="Invalid Scheme"
        )


def test_daily_nav_schema_validation():
    # Valid NAV
    nav_item = DailyNAVSchema(
        scheme_code=100027,
        date=date(2026, 7, 24),
        nav=75.43
    )
    assert nav_item.nav == 75.43

    # Invalid zero or negative NAV
    with pytest.raises(ValidationError):
        DailyNAVSchema(
            scheme_code=100027,
            date=date(2026, 7, 24),
            nav=-10.0
        )


def test_data_cleaner_parse_date():
    cleaner = DataCleaner()
    assert cleaner.parse_date("24-Jul-2026") == "2026-07-24"
    assert cleaner.parse_date("24-07-2026") == "2026-07-24"
    assert cleaner.parse_date("2026-07-24") == "2026-07-24"

    with pytest.raises(ValueError):
        cleaner.parse_date("invalid-date-string")


def test_data_cleaner_category_standardization():
    cleaner = DataCleaner()
    assert cleaner.standardize_category("Open Ended Schemes ( Equity Scheme - Large Cap Fund )") == "Equity - Large Cap"
    assert cleaner.standardize_category("Small Cap Fund") == "Equity - Small Cap"
    assert cleaner.standardize_category("Arbitrage Fund") == "Hybrid - Arbitrage"


def test_data_enricher_returns_calculation():
    raw_df = pd.DataFrame([
        {"scheme_code": 100027, "date": "2026-07-01", "nav": 100.0},
        {"scheme_code": 100027, "date": "2026-07-02", "nav": 110.0},  # +10%
        {"scheme_code": 100027, "date": "2026-07-03", "nav": 121.0},  # +10%
    ])

    df_enriched = DataEnricher.enrich_daily_nav_returns(raw_df)
    assert "daily_return" in df_enriched.columns
    assert "log_return" in df_enriched.columns
    assert "cumulative_return" in df_enriched.columns

    # 2nd day return should be 0.10 (10%)
    assert pytest.approx(df_enriched.iloc[1]["daily_return"], abs=1e-4) == 0.10
    # Cumulative return on 3rd day should be (121-100)/100 = 0.21 (21%)
    assert pytest.approx(df_enriched.iloc[2]["cumulative_return"], abs=1e-4) == 0.21


def test_transformation_pipeline_execution():
    pipeline = TransformationPipeline()
    summary = pipeline.run()

    assert summary["status"] == "SUCCESS"
    assert summary["metadata_rows"] > 0
    assert summary["daily_nav_rows"] > 0
    assert summary["benchmark_rows"] > 0

    processed_dir = pipeline.processed_dir
    assert (processed_dir / "clean_scheme_metadata.csv").exists()
    assert (processed_dir / "clean_daily_nav.parquet").exists()
    assert (processed_dir / "clean_benchmarks.parquet").exists()
