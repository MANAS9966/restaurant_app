"""
management/db_manager.py
Initialises and provides the Database singleton from configuration.
"""
from __future__ import annotations
import os
import logging

from management.config_manager import ConfigManager
from database.connection import Database
from database.schema import create_schema

log = logging.getLogger("restaurant_app.db")


class DBManager:
    """
    Reads SQLite path from ConfigManager, creates the Database singleton,
    and ensures the schema exists.
    """

    _instance: "DBManager | None" = None

    def __new__(cls, sqlite_path: str = None):
        if cls._instance is None:
            inst = super().__new__(cls)
            if sqlite_path is None:
                try:
                    sqlite_path = ConfigManager().sqlite_path()
                except Exception:
                    sqlite_path = "./data/restaurant.db"
            inst._path = sqlite_path
            inst._db: Database | None = None
            cls._instance = inst
        elif sqlite_path and cls._instance._path != sqlite_path:
            cls._instance._path = sqlite_path
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    # ------------------------------------------------------------------ init

    def initialise(self) -> Database:
        """Create (or reuse) the Database singleton and run schema creation."""
        # Resolve path relative to project root
        path = self._path
        if not os.path.isabs(path):
            root = os.path.join(os.path.dirname(__file__), "..")
            path = os.path.normpath(os.path.join(root, path))

        os.makedirs(os.path.dirname(path), exist_ok=True)

        try:
            self._db = Database(db_path=path)
        except ValueError:
            # Already initialised singleton
            self._db = Database()

        create_schema(self._db)
        log.info("Database initialised at: %s", path)
        return self._db

    @property
    def db(self) -> Database:
        if self._db is None:
            return self.initialise()
        return self._db

    # ------------------------------------------------------------------ health

    def ping(self) -> bool:
        """Return True if the database is reachable."""
        try:
            self.db.fetchone("SELECT 1 AS ok")
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Reset the underlying singleton database connection."""
        Database.reset()
        self._db = None

    def get_stats(self) -> dict:
        """Return basic row counts for health/admin dashboard."""
        try:
            db = self.db
            return {
                "users":  (db.fetchone("SELECT COUNT(*) AS n FROM users") or {}).get("n", 0),
                "owners": (db.fetchone("SELECT COUNT(*) AS n FROM restaurant_owners") or {}).get("n", 0),
                "dishes": (db.fetchone("SELECT COUNT(*) AS n FROM dishes") or {}).get("n", 0),
                "orders": (db.fetchone("SELECT COUNT(*) AS n FROM orders") or {}).get("n", 0),
            }
        except Exception:
            return {}
