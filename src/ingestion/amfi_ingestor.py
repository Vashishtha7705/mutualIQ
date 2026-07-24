"""
AMFI NAV Data Ingestor.
Fetches daily bulk Net Asset Value (NAV) data from official AMFI text feeds.
Includes network retry logic, exponential backoff, file landing, and raw parsing.
"""

from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import requests

from src.config.config_loader import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AMFIIngestor:
    """
    Ingestor client for AMFI official NAV data endpoint.
    """

    def __init__(self, amfi_url: Optional[str] = None, timeout: Optional[int] = None):
        config = get_config()
        self.amfi_url = amfi_url or config.get(
            "api.amfi_nav_url", "https://www.amfiindia.com/spages/NAVAll.txt"
        )
        self.timeout = timeout or config.get("api.timeout_seconds", 30)
        self.retry_attempts = config.get("api.retry_attempts", 3)
        self.backoff_factor = config.get("api.backoff_factor", 2.0)
        self.raw_dir = Path(config.get("paths.raw_data_dir", "data/raw"))
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def fetch_raw_nav_feed(self) -> str:
        """
        Downloads raw text content from the AMFI NAV endpoint with exponential backoff.
        
        Returns:
            str: Raw text content from AMFI.
            
        Raises:
            requests.RequestException: If all retry attempts fail.
        """
        logger.info("Connecting to AMFI NAV feed endpoint: %s", self.amfi_url)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MutualFundAnalyticsPlatform/1.0"
        }

        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = requests.get(self.amfi_url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                logger.info("Successfully fetched AMFI raw feed (%d bytes)", len(response.content))
                return response.text
            except requests.RequestException as exc:
                logger.warning(
                    "AMFI fetch attempt %d/%d failed: %s", attempt, self.retry_attempts, exc
                )
                if attempt == self.retry_attempts:
                    logger.error("All AMFI fetch retry attempts exhausted.")
                    raise
                sleep_time = self.backoff_factor ** (attempt - 1)
                logger.info("Waiting %.1f seconds before retry...", sleep_time)
                time.sleep(sleep_time)
        return ""

    def save_raw_feed(self, content: str, filename: str = "amfi_nav_latest.txt") -> Path:
        """
        Saves raw feed content to disk in data/raw.
        """
        file_path = self.raw_dir / filename
        file_path.write_text(content, encoding="utf-8")
        logger.info("Saved raw AMFI NAV feed to: %s", file_path)
        return file_path

    def parse_raw_feed(self, raw_text: str) -> List[Dict[str, Any]]:
        """
        Parses AMFI semicolon-delimited feed text into a list of structured records.
        
        Feed format sample:
        Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvest;Scheme Name;Net Asset Value;Date
        100027;INF846K01164;INF846K01172;Reliance Vision Fund - Growth Plan;34.5678;24-Jul-2026
        """
        records: List[Dict[str, Any]] = []
        current_category = "Uncategorized"
        current_fund_house = "Unknown"

        lines = raw_text.splitlines()
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Header or category lines detection
            if ";" not in line_str:
                if "Mutual Fund" in line_str or "Asset Management" in line_str or "AMC" in line_str:
                    current_fund_house = line_str
                elif "Schemes" in line_str:
                    current_category = line_str
                continue

            parts = [p.strip() for p in line_str.split(";")]
            # Ignore table header row
            if parts[0].lower() == "scheme code" or len(parts) < 6:
                continue

            scheme_code = parts[0]
            isin_payout = parts[1]
            isin_reinvest = parts[2]
            scheme_name = parts[3]
            nav_str = parts[4]
            date_str = parts[5]

            records.append({
                "scheme_code": scheme_code,
                "isin_payout": isin_payout,
                "isin_reinvest": isin_reinvest,
                "scheme_name": scheme_name,
                "nav": nav_str,
                "date": date_str,
                "category": current_category,
                "fund_house": current_fund_house
            })

        logger.info("Parsed %d raw NAV records from AMFI feed", len(records))
        return records

    def run(self) -> List[Dict[str, Any]]:
        """
        Executes full AMFI ingestion workflow: Fetch -> Save raw -> Parse records.
        """
        raw_text = self.fetch_raw_nav_feed()
        self.save_raw_feed(raw_text)
        return self.parse_raw_feed(raw_text)
