"""
database/dao/session_dao.py
CRUD for the sessions table.
"""
from __future__ import annotations
from database.dao.base_dao import BaseDAO


class SessionDAO(BaseDAO):

    def create_session(self, user_id: int, token: str,
                       ip_address: str = None, user_agent: str = None) -> dict:
        sql = """
            INSERT INTO sessions (user_id, session_token, ip_address, user_agent)
            VALUES (?, ?, ?, ?)
        """
        sid = self._insert(sql, (user_id, token, ip_address, user_agent))
        return self._fetchone("SELECT * FROM sessions WHERE id = ?", (sid,))

    def get_session(self, token: str) -> dict | None:
        return self._fetchone(
            "SELECT * FROM sessions WHERE session_token = ? AND logout_time IS NULL",
            (token,)
        )

    def update_session_activity(self, token: str) -> bool:
        self._execute(
            "UPDATE sessions SET last_activity = CURRENT_TIMESTAMP WHERE session_token = ?",
            (token,)
        )
        return True

    def end_session(self, token: str) -> bool:
        self._execute(
            "UPDATE sessions SET logout_time = CURRENT_TIMESTAMP WHERE session_token = ?",
            (token,)
        )
        return True

    def get_active_sessions(self) -> list[dict]:
        return self._fetchall(
            """SELECT s.*, u.full_name, u.email, u.role
               FROM sessions s
               JOIN users u ON s.user_id = u.id
               WHERE s.logout_time IS NULL
               ORDER BY s.last_activity DESC"""
        )

    def end_all_user_sessions(self, user_id: int) -> bool:
        self._execute(
            """UPDATE sessions SET logout_time = CURRENT_TIMESTAMP
               WHERE user_id = ? AND logout_time IS NULL""",
            (user_id,)
        )
        return True
