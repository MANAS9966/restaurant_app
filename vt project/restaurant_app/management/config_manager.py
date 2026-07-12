"""
management/config_manager.py
Loads, validates, and provides configuration to all layers.
Supports environment-variable overrides and hot-reload.
"""
from __future__ import annotations
import json
import os
import threading
from typing import Any

_DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "config.json"
)

_REQUIRED_SECTIONS = ("app", "database", "security", "mcp", "features")


class ConfigManager:
    """Singleton configuration manager."""

    _instance: "ConfigManager | None" = None
    _lock = threading.Lock()

    def __new__(cls, config_path: str = None):
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._path = config_path or _DEFAULT_CONFIG_PATH
                inst._config: dict = {}
                inst._load()
                cls._instance = inst
            elif config_path and cls._instance._path != config_path:
                cls._instance._path = config_path
                cls._instance._load()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton — for testing."""
        with cls._lock:
            cls._instance = None

    # ------------------------------------------------------------------ load

    def _load(self):
        path = self._path
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        self._validate(data)
        self._config = data

    def _validate(self, data: dict):
        for section in _REQUIRED_SECTIONS:
            if section not in data:
                raise ValueError(f"Config missing required section: '{section}'")

    def reload(self):
        """Hot-reload configuration from disk."""
        with self._lock:
            self._load()

    # ------------------------------------------------------------------ access

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Traverse nested config with dot-style keys.
        Example: cfg.get("database", "sqlite_path")
        """
        node = self._config
        for key in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(key, default)
            if node is default:
                return default
        # Environment variable override:  e.g. APP_DATABASE_SQLITE_PATH
        env_key = "APP_" + "_".join(k.upper() for k in keys)
        env_val = os.environ.get(env_key)
        return env_val if env_val is not None else node

    # ------------------------------------------------------------------ shortcuts

    @property
    def app(self) -> dict:
        return self._config.get("app", {})

    @property
    def database(self) -> dict:
        return self._config.get("database", {})

    @property
    def security(self) -> dict:
        return self._config.get("security", {})

    @property
    def mcp(self) -> dict:
        return self._config.get("mcp", {})

    @property
    def features(self) -> dict:
        return self._config.get("features", {})

    def window_size(self) -> tuple[int, int]:
        return (
            self.app.get("window_width", 1400),
            self.app.get("window_height", 900),
        )

    def sqlite_path(self) -> str:
        return self.database.get("sqlite_path", "./data/restaurant.db")

    def session_timeout_minutes(self) -> int:
        return self.security.get("session_timeout_minutes", 30)

    def max_login_attempts(self) -> int:
        return self.security.get("max_login_attempts", 5)

    def password_min_length(self) -> int:
        return self.security.get("password_min_length", 8)
