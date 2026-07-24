"""
Configuration Loader Module.
Loads YAML configuration files cleanly with singleton caching and validation.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import os
import yaml


class ConfigLoader:
    """
    Singleton Configuration Loader class that parses YAML configurations
    and resolves relative paths dynamically based on the project root directory.
    """

    _instance: Optional["ConfigLoader"] = None
    _config: Dict[str, Any] = {}

    def __new__(cls, config_path: Optional[str] = None) -> "ConfigLoader":
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._load_config(config_path)
        return cls._instance

    @classmethod
    def get_project_root(cls) -> Path:
        """
        Returns the absolute path to the root of the project directory.
        """
        # Resolves relative to this file: src/config/config_loader.py -> root is 2 levels up
        return Path(__file__).resolve().parent.parent.parent

    def _load_config(self, config_path: Optional[str] = None) -> None:
        """
        Reads YAML config file from disk.
        """
        project_root = self.get_project_root()
        
        if config_path is None:
            config_file = project_root / "config" / "config.yaml"
        else:
            config_file = Path(config_path)
            if not config_file.is_absolute():
                config_file = project_root / config_file

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found at: {config_file}")

        with open(config_file, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f) or {}

        # Resolve paths to absolute paths
        self._resolve_paths()

    def _resolve_paths(self) -> None:
        """
        Converts relative path strings in config under 'paths' to absolute Path objects.
        """
        project_root = self.get_project_root()
        if "paths" in self._config:
            for key, relative_path in self._config["paths"].items():
                abs_path = project_root / relative_path
                self._config["paths"][key] = str(abs_path)

    @property
    def config(self) -> Dict[str, Any]:
        """
        Returns the raw configuration dictionary.
        """
        return self._config

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Retrieves a nested configuration value using dot notation.
        Example: get('api.amfi_nav_url') or get('logging.level')
        """
        keys = key_path.split(".")
        val: Any = self._config
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val


def get_config(config_path: Optional[str] = None) -> ConfigLoader:
    """
    Helper function to get the ConfigLoader singleton instance.
    """
    return ConfigLoader(config_path)
