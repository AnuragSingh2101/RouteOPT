"""Configuration loader for RouteOpt."""

from pathlib import Path
from typing import Any
import yaml


class Config:
    """Configuration manager that loads from config.yaml."""

    _instance: "Config | None" = None
    _config: dict[str, Any]

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """Load configuration from config.yaml."""
        config_path = Path(__file__).parents[3] / "config.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation (e.g., 'solver.time_limit')."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def get_path(self, key: str) -> Path:
        """Get a path from config, resolved relative to project root."""
        project_root = Path(__file__).parents[3]
        rel_path = self.get(key)
        if rel_path is None:
            raise KeyError(f"Path not found in config: {key}")
        return project_root / rel_path

    @property
    def all(self) -> dict[str, Any]:
        """Return the entire configuration dictionary."""
        return self._config.copy()


def get_config() -> Config:
    """Get the singleton Config instance."""
    return Config()