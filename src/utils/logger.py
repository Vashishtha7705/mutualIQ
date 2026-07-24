"""
Centralized Enterprise Logging Framework.
Provides thread-safe logging with file rotation, custom console formatting,
and configurable log levels.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from src.config.config_loader import get_config


class ColoredConsoleFormatter(logging.Formatter):
    """
    Custom console formatter that adds ANSI color codes for enhanced readability.
    """

    GREY = "\x1b[38;20m"
    BLUE = "\x1b[34;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: GREY + "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s" + RESET,
        logging.INFO: BLUE + "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s" + RESET,
        logging.WARNING: YELLOW + "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s" + RESET,
        logging.ERROR: RED + "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s" + RESET,
        logging.CRITICAL: BOLD_RED + "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s" + RESET,
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno, self.FORMATS[logging.INFO])
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def get_logger(name: str = "mutual_fund_analytics", log_file: Optional[str] = None) -> logging.Logger:
    """
    Factory function to configure and return a named Logger instance.
    
    Args:
        name: Name of the logger module.
        log_file: Optional path override for log file.
        
    Returns:
        logging.Logger: Configured logger.
    """
    logger = logging.getLogger(name)

    # Return existing logger if handlers already attached to avoid duplication
    if logger.handlers:
        return logger

    config = get_config()
    log_level_str = config.get("logging.level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(log_level)

    # Console Handler (Colored)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(ColoredConsoleFormatter())
    logger.addHandler(console_handler)

    # File Handler (Rotating)
    target_log_file = log_file or config.get("paths.log_file")
    if target_log_file:
        log_path = Path(target_log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        max_bytes = config.get("logging.rotation_max_bytes", 10485760)
        backup_count = config.get("logging.backup_count", 5)

        file_handler = RotatingFileHandler(
            filename=log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_fmt = logging.Formatter(
            config.get("logging.format", "%(asctime)s | %(levelname)-8s | %(name)s - %(message)s"),
            datefmt=config.get("logging.date_format", "%Y-%m-%d %H:%M:%S")
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)

    return logger
