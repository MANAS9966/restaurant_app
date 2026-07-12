"""
management/session_manager.py
In-memory session lifecycle management.
Sessions expire after configured inactivity timeout.
"""
from __future__ import annotations
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from business_logic.exceptions import AuthorizationError


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Session:
    __slots__ = ("token", "user_id", "role", "login_time", "last_activity",
                 "user_data")

    def __init__(self, token: str, user_id: int, role: str, user_data: dict):
        self.token = token
        self.user_id = user_id
        self.role = role
        self.user_data = user_data        # full safe-user dict
        self.login_time = _now()
        self.last_activity = _now()

    def touch(self):
        self.last_activity = _now()

    def is_expired(self, timeout_minutes: int) -> bool:
        delta = _now() - self.last_activity
        return delta > timedelta(minutes=timeout_minutes)

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "user_id": self.user_id,
            "role": self.role,
            "login_time": self.login_time.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "user_data": self.user_data,
        }


class SessionManager:
    """Thread-safe in-memory session store."""

    _instance: Optional["SessionManager"] = None
    _cls_lock = threading.Lock()

    def __new__(cls, timeout_minutes: int = 30):
        with cls._cls_lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._sessions: dict[str, Session] = {}
                inst._lock = threading.Lock()
                inst._timeout = timeout_minutes
                cls._instance = inst
            elif timeout_minutes and cls._instance._timeout != timeout_minutes:
                cls._instance._timeout = timeout_minutes
        return cls._instance

    @classmethod
    def reset(cls):
        with cls._cls_lock:
            cls._instance = None

    # ------------------------------------------------------------------ API

    def create_session(self, user_data: dict) -> str:
        """
        Create a new session for *user_data* (must contain id, role).
        Returns the session token string.
        """
        token = str(uuid.uuid4())
        session = Session(
            token=token,
            user_id=user_data["id"],
            role=user_data["role"],
            user_data=user_data,
        )
        with self._lock:
            self._purge_expired()
            self._sessions[token] = session
        return token

    def get_session(self, token: str) -> Session:
        """
        Return the Session for *token*, raising AuthorizationError if invalid/expired.
        Touching last_activity on success.
        """
        with self._lock:
            session = self._sessions.get(token)
            if not session:
                raise AuthorizationError("Session not found. Please log in again.")
            if session.is_expired(self._timeout):
                del self._sessions[token]
                raise AuthorizationError(
                    "Your session has expired. Please log in again."
                )
            session.touch()
            return session

    def end_session(self, token: str) -> bool:
        with self._lock:
            return self._sessions.pop(token, None) is not None

    def get_active_sessions(self) -> list[dict]:
        """Return all non-expired sessions as dicts — admin feature."""
        with self._lock:
            self._purge_expired()
            return [s.to_dict() for s in self._sessions.values()]

    def force_logout(self, user_id: int) -> int:
        """Invalidate all sessions for *user_id*. Returns count removed."""
        with self._lock:
            tokens = [t for t, s in self._sessions.items()
                      if s.user_id == user_id]
            for t in tokens:
                del self._sessions[t]
        return len(tokens)

    def get_current_user(self, token: str) -> dict:
        """Convenience — returns user_data dict from session."""
        return self.get_session(token).user_data

    # ------------------------------------------------------------------ private

    def _purge_expired(self):
        """Remove expired sessions. Must be called under self._lock."""
        expired = [t for t, s in self._sessions.items()
                   if s.is_expired(self._timeout)]
        for t in expired:
            del self._sessions[t]
