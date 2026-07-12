"""
database/dao/order_dao.py
CRUD + status management for orders and order_items.
"""
from __future__ import annotations
from database.dao.base_dao import BaseDAO

# Valid status progression graph
STATUS_TRANSITIONS = {
    "pending":    ["confirmed", "cancelled"],
    "confirmed":  ["preparing", "cancelled"],
    "preparing":  ["on_the_way"],
    "on_the_way": ["delivered"],
    "delivered":  [],
    "cancelled":  [],
}


class OrderDAO(BaseDAO):

    # ------------------------------------------------------------------ orders

    def create_order(self, order_number: str, customer_id: int, owner_id: int,
                     subtotal: float, total_amount: float,
                     delivery_address: str, payment_method: str,
                     tax: float = 0, delivery_fee: float = 0,
                     discount_applied: float = 0,
                     special_instructions: str = None,
                     estimated_delivery_time: str = None) -> dict:
        sql = """
            INSERT INTO orders
            (order_number, customer_id, owner_id, subtotal, tax, delivery_fee,
             total_amount, discount_applied, delivery_address, payment_method,
             special_instructions, estimated_delivery_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        oid = self._insert(sql, (
            order_number, customer_id, owner_id,
            round(subtotal, 2), round(tax, 2), round(delivery_fee, 2),
            round(total_amount, 2), round(discount_applied, 2),
            delivery_address, payment_method,
            special_instructions, estimated_delivery_time
        ))
        return self.get_order_by_id(oid)

    def get_order_by_id(self, order_id: int) -> dict | None:
        return self._fetchone(
            """SELECT o.*, u.full_name AS customer_name, u.email AS customer_email,
                      ro.business_name
               FROM orders o
               JOIN users u ON o.customer_id = u.id
               JOIN restaurant_owners ro ON o.owner_id = ro.id
               WHERE o.id = ?""",
            (order_id,)
        )

    def get_order_by_number(self, order_number: str) -> dict | None:
        return self._fetchone(
            "SELECT * FROM orders WHERE order_number = ?", (order_number,)
        )

    def get_orders_by_customer(self, customer_id: int, status: str = None,
                               limit: int = 50, offset: int = 0) -> list[dict]:
        conditions = ["o.customer_id = ?"]
        params = [customer_id]
        if status:
            conditions.append("o.status = ?")
            params.append(status)
        where = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT o.*, ro.business_name
            FROM orders o
            JOIN restaurant_owners ro ON o.owner_id = ro.id
            {where}
            ORDER BY o.created_at DESC LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        return self._fetchall(sql, tuple(params))

    def get_orders_by_owner(self, owner_id: int, status: str = None,
                            limit: int = 50, offset: int = 0) -> list[dict]:
        conditions = ["o.owner_id = ?"]
        params = [owner_id]
        if status:
            conditions.append("o.status = ?")
            params.append(status)
        where = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT o.*, u.full_name AS customer_name
            FROM orders o
            JOIN users u ON o.customer_id = u.id
            {where}
            ORDER BY o.created_at DESC LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        return self._fetchall(sql, tuple(params))

    def get_all_orders(self, status: str = None, limit: int = 100,
                       offset: int = 0) -> list[dict]:
        params = []
        where = ""
        if status:
            where = "WHERE o.status = ?"
            params.append(status)
        sql = f"""
            SELECT o.*, u.full_name AS customer_name, ro.business_name
            FROM orders o
            JOIN users u ON o.customer_id = u.id
            JOIN restaurant_owners ro ON o.owner_id = ro.id
            {where}
            ORDER BY o.created_at DESC LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        return self._fetchall(sql, tuple(params))

    def update_order_status(self, order_id: int, new_status: str) -> bool:
        order = self._fetchone("SELECT status FROM orders WHERE id = ?", (order_id,))
        if not order:
            return False
        allowed = STATUS_TRANSITIONS.get(order["status"], [])
        if new_status not in allowed:
            raise ValueError(
                f"Invalid status transition: {order['status']} → {new_status}"
            )
        self._execute(
            "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_status, order_id)
        )
        if new_status == "delivered":
            self._execute(
                "UPDATE orders SET actual_delivery_time = CURRENT_TIMESTAMP WHERE id = ?",
                (order_id,)
            )
            self._execute(
                "UPDATE orders SET payment_status = 'completed' WHERE id = ?",
                (order_id,)
            )
        return True

    def cancel_order(self, order_id: int) -> bool:
        order = self._fetchone("SELECT status FROM orders WHERE id = ?", (order_id,))
        if not order or order["status"] not in ("pending", "confirmed"):
            return False
        self._execute(
            "UPDATE orders SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (order_id,)
        )
        return True

    # --------------------------------------------------------------- order items

    def add_order_item(self, order_id: int, dish_id: int, quantity: int,
                       unit_price: float, discount_at_time: float = 0) -> dict:
        subtotal = round(unit_price * quantity * (1 - discount_at_time / 100), 2)
        sql = """
            INSERT INTO order_items (order_id, dish_id, quantity, unit_price,
                                     discount_at_time, subtotal)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        item_id = self._insert(sql, (
            order_id, dish_id, quantity,
            round(unit_price, 2), round(discount_at_time, 2), subtotal
        ))
        return self._fetchone("SELECT * FROM order_items WHERE id = ?", (item_id,))

    def get_order_items(self, order_id: int) -> list[dict]:
        return self._fetchall(
            """SELECT oi.*, d.name AS dish_name, d.image_path
               FROM order_items oi
               JOIN dishes d ON oi.dish_id = d.id
               WHERE oi.order_id = ?""",
            (order_id,)
        )

    def remove_order_item(self, item_id: int) -> bool:
        self._execute("DELETE FROM order_items WHERE id = ?", (item_id,))
        return True

    def count_orders(self) -> int:
        return self._count("orders")
