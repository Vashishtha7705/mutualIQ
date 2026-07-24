"""
Data Ingestion Package
Provides clients and orchestrators for extracting daily and historical
mutual fund NAV data, scheme metadata, and benchmark indices.
"""

from src.ingestion.amfi_ingestor import AMFIIngestor
from src.ingestion.mfapi_ingestor import MFAPIIngestor
from src.ingestion.benchmark_ingestor import BenchmarkIngestor
from src.ingestion.pipeline import IngestionPipeline

__all__ = [
    "AMFIIngestor",
    "MFAPIIngestor",
    "BenchmarkIngestor",
    "IngestionPipeline",
]
