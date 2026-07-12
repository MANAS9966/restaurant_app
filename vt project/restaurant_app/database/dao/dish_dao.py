"""
database/dao/dish_dao.py
CRUD + search for the dishes table.
"""
from __future__ import annotations
from database.dao.base_dao import BaseDAO

VALID_CATEGORIES = [
    "appetizers", "mains", "desserts", "beverages",
    "salads", "soups", "sides", "burgers", "pizza",
    "pasta", "seafood", "breakfast", "specials"
]


class DishDAO(BaseDAO):

    def create_dish(self, owner_id: int, name: str, category: str, price: float,
                    description: str = None, max_discount_allowed: float = 30,
                    image_path: str = None) -> dict:
        sql = """
            INSERT INTO dishes
            (owner_id, name, category, price, description,
             max_discount_allowed, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        did = self._insert(sql, (
            owner_id, name, category, round(price, 2), description,
            max_discount_allowed, image_path
        ))
        return self.get_dish_by_id(did)

    def get_dish_by_id(self, dish_id: int) -> dict | None:
        return self._fetchone("SELECT * FROM dishes WHERE id = ?", (dish_id,))

    def get_dishes_by_owner(self, owner_id: int, filters: dict = None,
                            limit: int = 100, offset: int = 0) -> list[dict]:
        conditions = ["owner_id = ?"]
        params = [owner_id]
        if filters:
            for k, v in filters.items():
                conditions.append(f"{k} = ?")
                params.append(v)
        where = "WHERE " + " AND ".join(conditions)
        sql = f"SELECT * FROM dishes {where} ORDER BY name ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return self._fetchall(sql, tuple(params))

    def get_all_dishes(self, filters: dict = None, limit: int = 100,
                       offset: int = 0, search: str = None) -> list[dict]:
        """Returns dishes for customer browsing — includes owner business name."""
        conditions = ["d.status = 'active'"]
        params = []
        if filters:
            for k, v in filters.items():
                conditions.append(f"d.{k} = ?")
                params.append(v)
        if search:
            conditions.append("(d.name LIKE ? OR d.description LIKE ? OR ro.business_name LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like, like])
        where = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT d.*, ro.business_name, ro.city
            FROM dishes d
            JOIN restaurant_owners ro ON d.owner_id = ro.id
            {where}
            ORDER BY d.name ASC LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        return self._fetchall(sql, tuple(params))

    def search_dishes(self, query: str, category: str = None,
                      min_price: float = None, max_price: float = None,
                      owner_id: int = None, limit: int = 50,
                      offset: int = 0) -> list[dict]:
        conditions = ["d.status = 'active'"]
        params = []
        if query:
            conditions.append("(d.name LIKE ? OR d.description LIKE ?)")
            like = f"%{query}%"
            params.extend([like, like])
        if category:
            conditions.append("d.category = ?")
            params.append(category)
        if min_price is not None:
            conditions.append("d.price >= ?")
            params.append(min_price)
        if max_price is not None:
            conditions.append("d.price <= ?")
            params.append(max_price)
        if owner_id:
            conditions.append("d.owner_id = ?")
            params.append(owner_id)
        where = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT d.*, ro.business_name
            FROM dishes d
            JOIN restaurant_owners ro ON d.owner_id = ro.id
            {where}
            ORDER BY d.total_orders DESC, d.name ASC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        return self._fetchall(sql, tuple(params))

    def update_dish(self, dish_id: int, fields: dict) -> bool:
        if not fields:
            return False
        set_parts = [f"{k} = ?" for k in fields]
        set_parts.append("updated_at = CURRENT_TIMESTAMP")
        params = list(fields.values()) + [dish_id]
        self._execute(
            f"UPDATE dishes SET {', '.join(set_parts)} WHERE id = ?",
            tuple(params)
        )
        return True

    def update_dish_discount(self, dish_id: int, discount: float) -> bool:
        self._execute(
            "UPDATE dishes SET current_discount = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (round(discount, 2), dish_id)
        )
        return True

    def update_dish_status(self, dish_id: int, status: str) -> bool:
        self._execute(
            "UPDATE dishes SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, dish_id)
        )
        return True

    def delete_dish(self, dish_id: int) -> bool:
        self._execute("DELETE FROM dishes WHERE id = ?", (dish_id,))
        return True

    def has_active_orders(self, dish_id: int) -> bool:
        row = self._fetchone(
            """SELECT COUNT(*) AS cnt FROM order_items oi
               JOIN orders o ON oi.order_id = o.id
               WHERE oi.dish_id = ? AND o.status NOT IN ('delivered','cancelled')""",
            (dish_id,)
        )
        return (row["cnt"] or 0) > 0

    def increment_order_count(self, dish_id: int, qty: int = 1) -> bool:
        self._execute(
            "UPDATE dishes SET total_orders = total_orders + ? WHERE id = ?",
            (qty, dish_id)
        )
        return True

    def get_categories(self) -> list[str]:
        return VALID_CATEGORIES

    def count_dishes(self) -> int:
        return self._count("dishes")
