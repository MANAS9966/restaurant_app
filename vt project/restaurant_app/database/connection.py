"""
database/connection.py
SQLite connection pool with thread-safety and foreign key support.
"""
import sqlite3
import threading
import os
from datetime import datetime
from queue import Queue, Empty


def _convert_timestamp(value):
    """
    Parse SQLite TIMESTAMP values robustly.

    Handles:
    - SQLite CURRENT_TIMESTAMP format: YYYY-MM-DD HH:MM:SS
    - ISO 8601 strings with or without timezone
    - Unknown values are returned as text instead of raising during fetch
    """
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    text = str(value).strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text


sqlite3.register_converter("TIMESTAMP", _convert_timestamp)


class ConnectionPool:
    """Thread-safe SQLite connection pool."""

    def __init__(self, db_path: str, pool_size: int = 5):
        self._db_path = db_path
        self._pool_size = pool_size
        self._pool: Queue = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._local = threading.local()

        # Ensure data directory exists
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

        # Pre-fill the pool
        for _ in range(pool_size):
            conn = self._create_connection()
            self._pool.put(conn)

    def _create_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self._db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """Acquire a connection from the pool (blocks up to 5s)."""
        try:
            return self._pool.get(timeout=5)
        except Empty:
            # Create an overflow connection
            return self._create_connection()

    def release_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool."""
        try:
            self._pool.put_nowait(conn)
        except Exception:
            conn.close()

    def close_all(self):
        """Close all connections in the pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break


class Database:
    """Singleton database facade used by all DAOs."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = None):
        with cls._lock:
            if cls._instance is None:
                if db_path is None:
                    raise ValueError("db_path required on first instantiation")
                instance = super().__new__(cls)
                instance._pool = ConnectionPool(db_path)
                instance._db_path = db_path
                cls._instance = instance
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton — for testing only."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._pool.close_all()
            cls._instance = None

    def get_connection(self) -> sqlite3.Connection:
        return self._pool.get_connection()

    def release_connection(self, conn: sqlite3.Connection):
        self._pool.release_connection(conn)

    def execute(self, sql: str, params=()) -> sqlite3.Cursor:
        """Execute a single statement, auto-commit."""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            return cur
        finally:
            self.release_connection(conn)

    def fetchall(self, sql: str, params=()) -> list:
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
        finally:
            self.release_connection(conn)

    def fetchone(self, sql: str, params=()) -> dict | None:
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            self.release_connection(conn)

    def execute_many(self, sql: str, params_list: list):
        """Bulk insert with a single transaction."""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.executemany(sql, params_list)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self.release_connection(conn)

    def transaction(self):
        """Context manager for explicit transactions."""
        return _Transaction(self)


class _Transaction:
    """Context manager that holds a single connection for multi-step atomicity."""

    def __init__(self, db: Database):
        self._db = db
        self._conn: sqlite3.Connection = None

    def __enter__(self) -> sqlite3.Connection:
        self._conn = self._db.get_connection()
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self._db.release_connection(self._conn)
        return False  # re-raise exceptions
