"""
database/dao/audit_dao.py
Append-only audit log DAO.
"""
from __future__ import annotations
from database.dao.base_dao import BaseDAO
import json


class AuditDAO(BaseDAO):

    def log_operation(self, user_id: int, operation: str,
                      resource_type: str = None, resource_id: int = None,
                      old_value=None, new_value=None,
                      ip_address: str = None) -> bool:
        old_str = json.dumps(old_value) if old_value is not None else None
        new_str = json.dumps(new_value) if new_value is not None else None
        self._insert(
            """INSERT INTO audit_log
               (user_id, operation, resource_type, resource_id,
                old_value, new_value, ip_address)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, operation, resource_type, resource_id,
             old_str, new_str, ip_address)
        )
        return True

    def get_audit_log(self, user_id: int = None, resource_type: str = None,
                      limit: int = 100, offset: int = 0) -> list[dict]:
        conditions = []
        params = []
        if user_id:
            conditions.append("al.user_id = ?")
            params.append(user_id)
        if resource_type:
            conditions.append("al.resource_type = ?")
            params.append(resource_type)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"""
            SELECT al.*, u.full_name AS actor_name
            FROM audit_log al
            LEFT JOIN users u ON al.user_id = u.id
            {where}
            ORDER BY al.timestamp DESC LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        return self._fetchall(sql, tuple(params))
