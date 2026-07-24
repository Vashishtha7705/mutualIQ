"""
MFAPI Historical NAV Ingestor.
Fetches full historical NAV time-series and scheme metadata from mfapi.in API.
"""

import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import requests

from src.config.config_loader import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MFAPIIngestor:
    """
    Ingestor client for mfapi.in REST API.
    """

    def __init__(self, base_url: Optional[str] = None):
        config = get_config()
        self.base_url = base_url or config.get("api.mfapi_base_url", "https://api.mfapi.in/mf")
        self.timeout = config.get("api.timeout_seconds", 30)
        self.retry_attempts = config.get("api.retry_attempts", 3)
        self.backoff_factor = config.get("api.backoff_factor", 2.0)
        self.raw_dir = Path(config.get("paths.raw_data_dir", "data/raw"))
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def fetch_scheme_history(self, scheme_code: str) -> Dict[str, Any]:
        """
        Fetches historical NAV data for a specific mutual fund scheme code.
        
        Args:
            scheme_code (str): The AMFI scheme code (e.g., '100027' or '119551').
            
        Returns:
            Dict[str, Any]: JSON payload containing 'meta' and 'data' keys.
        """
        url = f"{self.base_url}/{scheme_code}"
        logger.info("Fetching historical NAV series for scheme code %s from %s", scheme_code, url)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MutualFundAnalyticsPlatform/1.0"
        }

        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = requests.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or "meta" not in data or "data" not in data:
                    logger.warning("Unexpected response payload structure for scheme %s", scheme_code)
                else:
                    logger.info(
                        "Successfully fetched %d historical NAV records for scheme %s",
                        len(data.get("data", [])),
                        scheme_code,
                    )
                return data
            except (requests.RequestException, ValueError) as exc:
                logger.warning(
                    "MFAPI fetch attempt %d/%d failed for scheme %s: %s",
                    attempt,
                    self.retry_attempts,
                    scheme_code,
                    exc,
                )
                if attempt == self.retry_attempts:
                    logger.error("Failed to fetch scheme %s history after %d attempts", scheme_code, self.retry_attempts)
                    raise
                sleep_time = self.backoff_factor ** (attempt - 1)
                time.sleep(sleep_time)

        return {}

    def save_scheme_raw_json(self, scheme_code: str, data: Dict[str, Any]) -> Path:
        """
        Saves raw JSON response to data/raw/scheme_{scheme_code}.json
        """
        file_path = self.raw_dir / f"scheme_{scheme_code}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("Saved scheme %s raw JSON to %s", scheme_code, file_path)
        return file_path

    def batch_fetch_schemes(self, scheme_codes: List[str], delay_seconds: float = 0.5) -> Dict[str, Dict[str, Any]]:
        """
        Fetches historical data for multiple scheme codes with rate-limiting pauses.
        """
        results = {}
        logger.info("Starting batch ingestion for %d scheme codes...", len(scheme_codes))
        for idx, code in enumerate(scheme_codes, 1):
            try:
                data = self.fetch_scheme_history(code)
                if data:
                    self.save_scheme_raw_json(code, data)
                    results[code] = data
            except Exception as exc:
                logger.error("Batch fetch error on scheme %s: %s", code, exc)

            if idx < len(scheme_codes) and delay_seconds > 0:
                time.sleep(delay_seconds)

        logger.info("Batch ingestion finished. Successfully ingested %d/%d schemes", len(results), len(scheme_codes))
        return results
