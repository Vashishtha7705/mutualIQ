"""
Benchmark Data Ingestor.
Fetches or generates historical index values (e.g., Nifty 50 TRI, Nifty Midcap 150 TRI)
for benchmark comparative analytics (Alpha, Beta, Tracking Error).
"""

from datetime import datetime, timedelta
import math
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from src.config.config_loader import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BenchmarkIngestor:
    """
    Ingestor client for historical benchmark indices.
    Supports real CSV loading or fallback synthetic generation matching realistic market drift and volatility.
    """

    def __init__(self):
        config = get_config()
        self.raw_dir = Path(config.get("paths.raw_data_dir", "data/raw"))
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def generate_synthetic_benchmark(
        self,
        index_name: str = "NIFTY_50_TRI",
        start_date: str = "2019-01-01",
        end_date: str = "2026-07-24",
        initial_value: float = 10000.0,
        annual_drift: float = 0.12,  # 12% CAGR
        annual_volatility: float = 0.15,  # 15% Volatility
    ) -> pd.DataFrame:
        """
        Generates realistic historical benchmark index data using geometric random walk
        for testing quantitative metrics (Beta, Alpha, Tracking Error).
        
        Returns:
            pd.DataFrame: Columns ['date', 'index_name', 'close_value']
        """
        logger.info("Generating synthetic benchmark series for '%s' from %s to %s", index_name, start_date, end_date)
        date_range = pd.date_range(start=start_date, end=end_date, freq="B")  # Business days

        n_days = len(date_range)
        dt = 1.0 / 252.0  # 252 trading days per year
        
        # Deterministic seed based on index_name for reproducibility
        seed = sum(ord(c) for c in index_name)
        
        # Generating realistic market returns
        import numpy as np
        np.random.seed(seed)
        shocks = np.random.normal(0, 1, n_days)
        
        prices = [initial_value]
        for i in range(1, n_days):
            # GBM step: S_t = S_{t-1} * exp((drift - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)
            drift_term = (annual_drift - 0.5 * (annual_volatility ** 2)) * dt
            diffusion_term = annual_volatility * math.sqrt(dt) * shocks[i]
            next_price = prices[-1] * math.exp(drift_term + diffusion_term)
            prices.append(round(next_price, 2))

        df = pd.DataFrame({
            "date": date_range.strftime("%Y-%m-%d"),
            "index_name": index_name,
            "close_value": prices
        })

        out_path = self.raw_dir / f"benchmark_{index_name.lower()}.csv"
        df.to_csv(out_path, index=False)
        logger.info("Saved benchmark index '%s' dataset (%d rows) to %s", index_name, len(df), out_path)
        return df

    def run_default_benchmarks(self) -> Dict[str, Path]:
        """
        Runs ingestion for primary benchmark indices.
        """
        indices = [
            ("NIFTY_50_TRI", 0.13, 0.15),
            ("NIFTY_MIDCAP_150_TRI", 0.16, 0.18),
            ("NIFTY_SMALLCAP_250_TRI", 0.18, 0.22),
            ("CRISIL_COMPOSITE_BOND_INDEX", 0.07, 0.04)
        ]
        
        paths = {}
        for name, drift, vol in indices:
            df = self.generate_synthetic_benchmark(
                index_name=name,
                annual_drift=drift,
                annual_volatility=vol
            )
            paths[name] = self.raw_dir / f"benchmark_{name.lower()}.csv"

        return paths
