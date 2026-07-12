"""
database/dao/user_dao.py
CRUD operations for the users table.
"""
from __future__ import annotations
from database.dao.base_dao import BaseDAO
from database.connection import Database


class UserDAO(BaseDAO):

    def create_user(self, email: str, password_hash: str, full_name: str,
                    role: str = "customer", phone: str = None,
                    address: str = None) -> dict:
        sql = """
            INSERT INTO users (email, password_hash, full_name, role, phone, address)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        uid = self._insert(sql, (email, password_hash, full_name, role, phone, address))
        return self.get_user_by_id(uid)

    def get_user_by_id(self, user_id: int) -> dict | None:
        return self._fetchone("SELECT * FROM users WHERE id = ?", (user_id,))

    def get_user_by_email(self, email: str) -> dict | None:
        return self._fetchone("SELECT * FROM users WHERE email = ?", (email,))

    def get_all_users(self, filters: dict = None, limit: int = 100,
                      offset: int = 0, search: str = None) -> list[dict]:
        conditions = []
        params = []

        if filters:
            for k, v in filters.items():
                conditions.append(f"{k} = ?")
                params.append(v)

        if search:
            conditions.append("(full_name LIKE ? OR email LIKE ? OR phone LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like, like])

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT * FROM users {where} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return self._fetchall(sql, tuple(params))

    def update_user(self, user_id: int, fields: dict) -> bool:
        if not fields:
            return False
        fields["updated_at"] = "CURRENT_TIMESTAMP"
        # Build manually to handle CURRENT_TIMESTAMP keyword
        set_parts = []
        params = []
        for k, v in fields.items():
            if v == "CURRENT_TIMESTAMP":
                set_parts.append(f"{k} = CURRENT_TIMESTAMP")
            else:
                set_parts.append(f"{k} = ?")
                params.append(v)
        params.append(user_id)
        sql = f"UPDATE users SET {', '.join(set_parts)} WHERE id = ?"
        self._execute(sql, tuple(params))
        return True

    def update_user_status(self, user_id: int, status: str) -> bool:
        self._execute(
            "UPDATE users SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, user_id)
        )
        return True

    def update_login_attempt(self, user_id: int, reset: bool = False,
                             locked_until: str = None) -> bool:
        if reset:
            sql = ("UPDATE users SET failed_login_attempts = 0, locked_until = NULL,"
                   " last_login = CURRENT_TIMESTAMP WHERE id = ?")
            self._execute(sql, (user_id,))
        else:
            sql = ("UPDATE users SET failed_login_attempts = failed_login_attempts + 1,"
                   " locked_until = ? WHERE id = ?")
            self._execute(sql, (locked_until, user_id))
        return True

    def delete_user(self, user_id: int) -> bool:
        self._execute("DELETE FROM users WHERE id = ?", (user_id,))
        return True

    def count_users(self, role: str = None) -> int:
        if role:
            return self._count("users", "role = ?", (role,))
        return self._count("users")

    def get_all_user_count_by_role(self) -> dict:
        rows = self._fetchall(
            "SELECT role, COUNT(*) as cnt FROM users GROUP BY role"
        )
        return {r["role"]: r["cnt"] for r in rows}
