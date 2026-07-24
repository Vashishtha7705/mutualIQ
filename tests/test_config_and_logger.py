"""
Unit tests for Configuration Loader and Logger utilities.
"""

from pathlib import Path
import pytest
from src.config.config_loader import ConfigLoader, get_config
from src.utils.logger import get_logger


def test_config_loader_singleton():
    cfg1 = ConfigLoader()
    cfg2 = get_config()
    assert cfg1 is cfg2


def test_config_values():
    cfg = get_config()
    assert cfg.get("app.name") == "Mutual Fund Analytics Platform"
    assert cfg.get("financial_defaults.risk_free_rate") == 0.065
    assert cfg.get("non_existent_key", "default_val") == "default_val"


def test_config_path_resolution():
    cfg = get_config()
    db_path = cfg.get("paths.database_path")
    assert db_path is not None
    assert Path(db_path).is_absolute()


def test_logger_creation():
    logger = get_logger("test_module")
    assert logger.name == "test_module"
    assert len(logger.handlers) >= 1
