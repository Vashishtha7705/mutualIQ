"""
Unit test suite for Module 2 Data Ingestion & Extraction Layer.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
import requests

from src.ingestion.amfi_ingestor import AMFIIngestor
from src.ingestion.mfapi_ingestor import MFAPIIngestor
from src.ingestion.benchmark_ingestor import BenchmarkIngestor
from src.ingestion.pipeline import IngestionPipeline


# Sample AMFI raw response block
MOCK_AMFI_RESPONSE = """Open Ended Schemes ( Equity Scheme - Large Cap Fund )
Mutual Fund Name: HDFC Mutual Fund
Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvest;Scheme Name;Net Asset Value;Date
100027;INF846K01164;INF846K01172;SBI Bluechip Fund - Direct Plan - Growth;75.4321;24-Jul-2026
119551;INF209K01157;INF209K01165;Mirae Asset Large Cap Fund - Direct Plan - Growth;98.1234;24-Jul-2026
"""

# Sample MFAPI raw response payload
MOCK_MFAPI_RESPONSE = {
    "meta": {
        "fund_house": "SBI Mutual Fund",
        "scheme_type": "Open Ended Schemes",
        "scheme_category": "Equity Scheme - Large Cap Fund",
        "scheme_code": 100027,
        "scheme_name": "SBI Bluechip Fund - Direct Plan - Growth"
    },
    "data": [
        {"date": "24-07-2026", "nav": "75.4321"},
        {"date": "23-07-2026", "nav": "74.9800"},
        {"date": "22-07-2026", "nav": "74.5000"}
    ]
}


def test_amfi_ingestor_parse():
    ingestor = AMFIIngestor()
    records = ingestor.parse_raw_feed(MOCK_AMFI_RESPONSE)
    assert len(records) == 2
    assert records[0]["scheme_code"] == "100027"
    assert records[0]["nav"] == "75.4321"
    assert records[1]["scheme_code"] == "119551"


@patch("requests.get")
def test_amfi_ingestor_fetch(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = MOCK_AMFI_RESPONSE.encode("utf-8")
    mock_response.text = MOCK_AMFI_RESPONSE
    mock_get.return_value = mock_response

    ingestor = AMFIIngestor()
    text = ingestor.fetch_raw_nav_feed()
    assert "SBI Bluechip Fund" in text


@patch("requests.get")
def test_mfapi_ingestor_fetch(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_MFAPI_RESPONSE
    mock_get.return_value = mock_response

    ingestor = MFAPIIngestor()
    data = ingestor.fetch_scheme_history("100027")
    assert data["meta"]["scheme_code"] == 100027
    assert len(data["data"]) == 3


def test_benchmark_ingestor_generation(tmp_path):
    ingestor = BenchmarkIngestor()
    # Override raw_dir with tmp_path for test isolation
    ingestor.raw_dir = tmp_path

    df = ingestor.generate_synthetic_benchmark(
        index_name="TEST_INDEX",
        start_date="2024-01-01",
        end_date="2024-01-10",
        initial_value=100.0
    )

    assert isinstance(df, pd.DataFrame)
    assert "date" in df.columns
    assert "close_value" in df.columns
    assert len(df) > 0
    assert (tmp_path / "benchmark_test_index.csv").exists()


@patch("src.ingestion.amfi_ingestor.AMFIIngestor.fetch_raw_nav_feed", return_value=MOCK_AMFI_RESPONSE)
@patch("src.ingestion.mfapi_ingestor.MFAPIIngestor.fetch_scheme_history", return_value=MOCK_MFAPI_RESPONSE)
def test_ingestion_pipeline(mock_mfapi, mock_amfi):
    pipeline = IngestionPipeline(target_scheme_codes=["100027"])
    summary = pipeline.run()

    assert summary["status"] == "SUCCESS"
    assert summary["amfi_records_count"] == 2
    assert summary["schemes_ingested_count"] == 1
    assert summary["benchmarks_ingested_count"] == 4
