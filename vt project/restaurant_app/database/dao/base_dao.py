"""
database/dao/base_dao.py
Abstract base DAO with common helpers shared by all DAOs.
"""
from __future__ import annotations
from typing import Any
from database.connection import Database


class BaseDAO:
    """Base class for all Data Access Objects."""

    def __init__(self, db: Database):
        self._db = db

    # ------------------------------------------------------------------ helpers

    def _fetchone(self, sql: str, params: tuple = ()) -> dict | None:
        return self._db.fetchone(sql, params)

    def _fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        return self._db.fetchall(sql, params)

    def _execute(self, sql: str, params: tuple = ()):
        return self._db.execute(sql, params)

    def _insert(self, sql: str, params: tuple = ()) -> int:
        """Execute INSERT and return lastrowid."""
        cur = self._db.execute(sql, params)
        return cur.lastrowid

    def _count(self, table: str, where: str = "", params: tuple = ()) -> int:
        clause = f"WHERE {where}" if where else ""
        row = self._fetchone(f"SELECT COUNT(*) AS cnt FROM {table} {clause}", params)
        return row["cnt"] if row else 0

    def _build_set_clause(self, fields: dict) -> tuple[str, tuple]:
        """Return (SET clause string, values tuple) for UPDATE statements."""
        parts = [f"{k} = ?" for k in fields]
        return ", ".join(parts), tuple(fields.values())

    def _build_filter_clause(self, filters: dict) -> tuple[str, tuple]:
        """Return (WHERE clause string, values tuple) for SELECT statements."""
        if not filters:
            return "", ()
        parts = [f"{k} = ?" for k in filters]
        return "WHERE " + " AND ".join(parts), tuple(filters.values())
