"""
database/dao/owner_dao.py
CRUD operations for the restaurant_owners table.
"""
from __future__ import annotations
from database.dao.base_dao import BaseDAO


class OwnerDAO(BaseDAO):

    def create_owner(self, user_id: int, business_name: str, license_number: str,
                     phone: str = None, email: str = None, city: str = None,
                     state: str = None, postal_code: str = None,
                     license_image_path: str = None) -> dict:
        sql = """
            INSERT INTO restaurant_owners
            (user_id, business_name, license_number, phone, email,
             city, state, postal_code, license_image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        oid = self._insert(sql, (
            user_id, business_name, license_number, phone, email,
            city, state, postal_code, license_image_path
        ))
        return self.get_owner_by_id(oid)

    def get_owner_by_id(self, owner_id: int) -> dict | None:
        return self._fetchone("SELECT * FROM restaurant_owners WHERE id = ?", (owner_id,))

    def get_owner_by_user_id(self, user_id: int) -> dict | None:
        return self._fetchone(
            "SELECT * FROM restaurant_owners WHERE user_id = ?", (user_id,)
        )

    def get_all_owners(self, filters: dict = None, limit: int = 100,
                       offset: int = 0, search: str = None) -> list[dict]:
        conditions = []
        params = []

        if filters:
            for k, v in filters.items():
                conditions.append(f"ro.{k} = ?")
                params.append(v)

        if search:
            conditions.append(
                "(ro.business_name LIKE ? OR u.full_name LIKE ? OR ro.email LIKE ?)"
            )
            like = f"%{search}%"
            params.extend([like, like, like])

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"""
            SELECT ro.*, u.full_name AS owner_full_name, u.email AS owner_user_email
            FROM restaurant_owners ro
            JOIN users u ON ro.user_id = u.id
            {where}
            ORDER BY ro.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        return self._fetchall(sql, tuple(params))

    def update_owner(self, owner_id: int, fields: dict) -> bool:
        if not fields:
            return False
        set_parts = []
        params = []
        for k, v in fields.items():
            set_parts.append(f"{k} = ?")
            params.append(v)
        set_parts.append("updated_at = CURRENT_TIMESTAMP")
        params.append(owner_id)
        sql = f"UPDATE restaurant_owners SET {', '.join(set_parts)} WHERE id = ?"
        self._execute(sql, tuple(params))
        return True

    def update_verification_status(self, owner_id: int, status: str,
                                   verified_by: int = None,
                                   rejection_reason: str = None) -> bool:
        self._execute(
            """UPDATE restaurant_owners
               SET verification_status = ?, verified_by = ?,
                   rejection_reason = ?, verification_date = CURRENT_TIMESTAMP,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (status, verified_by, rejection_reason, owner_id)
        )
        return True

    def get_owner_analytics(self, owner_id: int) -> dict:
        dishes = self._fetchone(
            "SELECT COUNT(*) AS total, SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS active"
            " FROM dishes WHERE owner_id = ?", (owner_id,)
        ) or {}
        orders = self._fetchone(
            "SELECT COUNT(*) AS total_orders, SUM(total_amount) AS revenue"
            " FROM orders WHERE owner_id = ? AND status != 'cancelled'", (owner_id,)
        ) or {}
        popular = self._fetchone(
            """SELECT d.name, SUM(oi.quantity) AS units
               FROM order_items oi
               JOIN dishes d ON oi.dish_id = d.id
               WHERE d.owner_id = ?
               GROUP BY d.id ORDER BY units DESC LIMIT 1""",
            (owner_id,)
        )
        return {
            "total_dishes": dishes.get("total", 0) or 0,
            "active_dishes": dishes.get("active", 0) or 0,
            "total_orders": orders.get("total_orders", 0) or 0,
            "total_revenue": round(orders.get("revenue", 0) or 0, 2),
            "most_popular_dish": popular["name"] if popular else "N/A",
        }

    def update_total_dishes(self, owner_id: int) -> bool:
        self._execute(
            """UPDATE restaurant_owners SET total_dishes =
               (SELECT COUNT(*) FROM dishes WHERE owner_id = ? AND status='active')
               WHERE id = ?""",
            (owner_id, owner_id)
        )
        return True

    def count_owners(self, verification_status: str = None) -> int:
        if verification_status:
            return self._count("restaurant_owners", "verification_status = ?",
                               (verification_status,))
        return self._count("restaurant_owners")
