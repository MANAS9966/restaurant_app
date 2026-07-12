"""
business_logic/order_manager.py
Business logic for order creation, status transitions, and history.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone

from business_logic.exceptions import (
    ValidationError, AuthorizationError, NotFoundError, OrderStateError
)
from business_logic.discount_manager import DiscountManager
from business_logic.logger import log
from database.dao.order_dao import OrderDAO
from database.dao.dish_dao import DishDAO
from database.dao.owner_dao import OwnerDAO
from database.dao.audit_dao import AuditDAO

TAX_RATE = 0.10          # 10%
DELIVERY_FEE = 5.99
VALID_PAYMENT_METHODS = ("credit_card", "debit_card", "wallet", "cash_on_delivery")
ESTIMATED_DELIVERY_MINUTES = 45


def _utcnow():
    return datetime.now(timezone.utc)


def _sqlite_timestamp(dt: datetime) -> str:
    """Format datetimes for SQLite TIMESTAMP columns."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


class OrderManager:

    def __init__(self, order_dao: OrderDAO, dish_dao: DishDAO,
                 owner_dao: OwnerDAO, audit_dao: AuditDAO,
                 discount_manager: DiscountManager = None):
        self._orders = order_dao
        self._dishes = dish_dao
        self._owners = owner_dao
        self._audit = audit_dao
        self._discount = discount_manager

    def _gen_order_number(self) -> str:
        return f"ORD-{uuid.uuid4().hex[:10].upper()}"

    # ---------------------------------------------------------------- create

    def create_order(self, customer_id: int, cart_items: list[dict],
                     delivery_address: str, payment_method: str,
                     special_instructions: str = None) -> dict:
        """
        cart_items: list of {"dish_id": int, "quantity": int}
        Returns the full order dict.
        """
        if not cart_items:
            raise ValidationError("Cart is empty.")
        if payment_method not in VALID_PAYMENT_METHODS:
            raise ValidationError(
                f"Payment method must be one of: {', '.join(VALID_PAYMENT_METHODS)}"
            )
        if not delivery_address or not delivery_address.strip():
            raise ValidationError("Delivery address is required.")

        # Validate items and determine owner
        owner_id = None
        resolved_items = []
        for item in cart_items:
            dish_id = item.get("dish_id")
            qty = item.get("quantity", 1)
            if not dish_id:
                raise ValidationError("Each cart item must have a dish_id.")
            if not isinstance(qty, int) or qty < 1:
                raise ValidationError("Quantity must be a positive integer.")

            dish = self._dishes.get_dish_by_id(dish_id)
            if not dish or dish["status"] != "active":
                raise ValidationError(
                    f"Dish {dish_id} is not available."
                )

            if owner_id is None:
                owner_id = dish["owner_id"]
            elif owner_id != dish["owner_id"]:
                raise ValidationError(
                    "All items in an order must be from the same restaurant."
                )

            effective_price = DiscountManager.calculate_final_price(
                dish["price"], dish["current_discount"] or 0
            )
            resolved_items.append({
                "dish_id": dish_id,
                "quantity": qty,
                "unit_price": dish["price"],
                "discount_at_time": dish["current_discount"] or 0,
                "effective_price": effective_price,
                "name": dish["name"],
            })

        subtotal = round(sum(i["effective_price"] * i["quantity"]
                             for i in resolved_items), 2)
        tax = round(subtotal * TAX_RATE, 2)
        total = round(subtotal + tax + DELIVERY_FEE, 2)
        estimated = (
            _utcnow() + timedelta(minutes=ESTIMATED_DELIVERY_MINUTES)
        )
        estimated = _sqlite_timestamp(estimated)

        order_number = self._gen_order_number()

        # Atomic transaction: order + items
        conn = self._orders._db.get_connection()
        try:
            # Insert order
            cur = conn.execute(
                """INSERT INTO orders
                   (order_number, customer_id, owner_id, subtotal, tax, delivery_fee,
                    total_amount, delivery_address, payment_method,
                    special_instructions, estimated_delivery_time)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (order_number, customer_id, owner_id, subtotal, tax, DELIVERY_FEE,
                 total, delivery_address.strip(), payment_method,
                 special_instructions, estimated)
            )
            order_id = cur.lastrowid

            # Insert items
            for item in resolved_items:
                item_subtotal = round(item["effective_price"] * item["quantity"], 2)
                conn.execute(
                    """INSERT INTO order_items
                       (order_id, dish_id, quantity, unit_price,
                        discount_at_time, subtotal)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (order_id, item["dish_id"], item["quantity"],
                     item["unit_price"], item["discount_at_time"], item_subtotal)
                )
                # Increment dish order count
                conn.execute(
                    "UPDATE dishes SET total_orders = total_orders + ? WHERE id = ?",
                    (item["quantity"], item["dish_id"])
                )
            conn.commit()
        except Exception:
            conn.rollback()
            self._orders._db.release_connection(conn)
            raise
        self._orders._db.release_connection(conn)

        self._audit.log_operation(customer_id, "ORDER_CREATED",
                                  "order", order_id, new_value={"order_number": order_number})
        log.info("Order %s created by customer %s", order_number, customer_id)
        return self.get_order(order_id, customer_id, "customer")

    # ---------------------------------------------------------------- read

    def get_order(self, order_id: int, actor_id: int, actor_role: str) -> dict:
        order = self._orders.get_order_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order {order_id} not found.")
        self._check_order_access(order, actor_id, actor_role)
        order["items"] = self._orders.get_order_items(order_id)
        return order

    def get_customer_orders(self, customer_id: int, actor_id: int,
                            actor_role: str, status: str = None,
                            limit: int = 50, offset: int = 0) -> list[dict]:
        if actor_role not in ("admin",) and actor_id != customer_id:
            raise AuthorizationError("You can only view your own orders.")
        return self._orders.get_orders_by_customer(customer_id, status, limit, offset)

    def get_owner_orders(self, owner_id: int, actor_user_id: int,
                         actor_role: str, status: str = None,
                         limit: int = 50, offset: int = 0) -> list[dict]:
        owner = self._owners.get_owner_by_id(owner_id)
        if not owner:
            raise NotFoundError(f"Owner {owner_id} not found.")
        if actor_role != "admin" and owner["user_id"] != actor_user_id:
            raise AuthorizationError("You can only view orders for your own restaurant.")
        return self._orders.get_orders_by_owner(owner_id, status, limit, offset)

    def get_all_orders(self, actor_role: str, status: str = None,
                       limit: int = 100, offset: int = 0) -> list[dict]:
        if actor_role != "admin":
            raise AuthorizationError("Only admins can view all orders.")
        return self._orders.get_all_orders(status, limit, offset)

    # ---------------------------------------------------------------- update

    def update_order_status(self, order_id: int, new_status: str,
                            actor_id: int, actor_role: str) -> dict:
        order = self._orders.get_order_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order {order_id} not found.")

        # Permission: admin or the owning restaurant
        if actor_role != "admin":
            owner = self._owners.get_owner_by_user_id(actor_id)
            if not owner or owner["id"] != order["owner_id"]:
                raise AuthorizationError(
                    "Only the restaurant owner or admin can update order status."
                )

        try:
            self._orders.update_order_status(order_id, new_status)
        except ValueError as e:
            raise OrderStateError(str(e))

        self._audit.log_operation(
            actor_id, "ORDER_STATUS_CHANGED", "order", order_id,
            old_value={"status": order["status"]},
            new_value={"status": new_status}
        )
        return self.get_order(order_id, actor_id, actor_role)

    def cancel_order(self, order_id: int, actor_id: int, actor_role: str) -> dict:
        order = self._orders.get_order_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order {order_id} not found.")
        self._check_order_access(order, actor_id, actor_role)
        if not self._orders.cancel_order(order_id):
            raise OrderStateError(
                f"Order cannot be cancelled in its current status: {order['status']}"
            )
        self._audit.log_operation(actor_id, "ORDER_CANCELLED", "order", order_id)
        return self.get_order(order_id, actor_id, actor_role)

    # ---------------------------------------------------------------- helpers

    def _check_order_access(self, order: dict, actor_id: int, actor_role: str):
        if actor_role == "admin":
            return
        if actor_role == "customer" and order["customer_id"] == actor_id:
            return
        if actor_role == "owner":
            owner = self._owners.get_owner_by_user_id(actor_id)
            if owner and owner["id"] == order["owner_id"]:
                return
        raise AuthorizationError("You do not have permission to access this order.")
