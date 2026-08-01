"""
Unit test suite for Module 10 Power BI Integration & Exporter.
"""

from pathlib import Path
import pandas as pd
import pytest

from src.database.db_manager import DatabaseManager
from src.database.loader import DatabaseLoader
from src.database.powerbi_export import PowerBIExporter


@pytest.fixture
def test_db_for_powerbi(tmp_path):
    db_file = tmp_path / "test_pbi.db"
    mgr = DatabaseManager(f"sqlite:///{db_file}", force_new=True)
    mgr.create_tables()

    loader = DatabaseLoader(mgr)
    loader.seed_date_dimension("2026-07-20", "2026-07-24")
    loader.seed_investor_dimension()

    yield mgr


def test_powerbi_export_pipeline(test_db_for_powerbi, tmp_path):
    exporter = PowerBIExporter(test_db_for_powerbi)
    # Redirect export dir for test isolation
    exporter.export_dir = tmp_path / "powerbi_test"
    exporter.export_dir.mkdir(parents=True, exist_ok=True)

    files = exporter.export_all_tables()

    assert len(files) >= 5
    assert "dim_date" in files
    assert "dim_investor" in files
    assert files["dim_date"].exists()

    df_date = pd.read_csv(files["dim_date"])
    assert not df_date.empty
    assert "date_id" in df_date.columns
