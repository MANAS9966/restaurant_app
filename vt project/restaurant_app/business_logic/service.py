"""
business_logic/service.py
Orchestration facade — single entry point used by the UI layer.
All managers are wired together here.
"""
from __future__ import annotations

from business_logic.exceptions import ValidationError
from business_logic.logger import log
from database.connection import Database
from database.dao.user_dao import UserDAO
from database.dao.owner_dao import OwnerDAO
from database.dao.dish_dao import DishDAO
from database.dao.order_dao import OrderDAO
from database.dao.session_dao import SessionDAO
from database.dao.audit_dao import AuditDAO

from business_logic.user_manager import UserManager
from business_logic.owner_manager import OwnerManager
from business_logic.dish_manager import DishManager
from business_logic.discount_manager import DiscountManager
from business_logic.order_manager import OrderManager


class RestaurantService:
    """Wires all DAOs and managers together for use by the UI."""

    def __init__(self, db: Database, password_min_length: int = 8):
        # DAOs
        self.user_dao    = UserDAO(db)
        self.owner_dao   = OwnerDAO(db)
        self.dish_dao    = DishDAO(db)
        self.order_dao   = OrderDAO(db)
        self.session_dao = SessionDAO(db)
        self.audit_dao   = AuditDAO(db)

        # Managers
        self.users    = UserManager(self.user_dao, self.audit_dao, password_min_length)
        self.owners   = OwnerManager(self.owner_dao, self.user_dao, self.audit_dao)
        self.discounts = DiscountManager(self.dish_dao, self.audit_dao)
        self.dishes   = DishManager(self.dish_dao, self.owner_dao,
                                    self.audit_dao, self.discounts)
        self.orders   = OrderManager(self.order_dao, self.dish_dao,
                                     self.owner_dao, self.audit_dao,
                                     self.discounts)

    # Convenience shortcuts (pass-through to avoid deep dot-chaining in UI)

    def login(self, email: str, password: str) -> dict:
        return self.users.login(email, password)

    def register_user(self, email, password, full_name, role="customer",
                      phone=None, address=None) -> dict:
        return self.users.register(email, password, full_name, role, phone, address)

    def set_user_status(self, actor_role: str, target_id: int, status: str) -> dict:
        return self.users.set_user_status(actor_role, target_id, status)

    def create_dish(self, actor_user_id: int, actor_role: str, **fields) -> dict:
        return self.dishes.create_dish(actor_user_id, actor_role, **fields)

    def update_dish(self, actor_user_id: int, actor_role: str, dish_id: int, fields: dict) -> dict:
        return self.dishes.update_dish(actor_user_id, actor_role, dish_id, fields)

    def toggle_dish_status(self, actor_user_id: int, actor_role: str, dish_id: int) -> dict:
        return self.dishes.toggle_dish_status(actor_user_id, actor_role, dish_id)

    def delete_dish(self, actor_user_id: int, actor_role: str, dish_id: int) -> bool:
        return self.dishes.delete_dish(actor_user_id, actor_role, dish_id)

    def get_dishes(self, **filters) -> list[dict]:
        return self.dishes.get_all_dishes(**filters)

    def create_order(self, customer_id: int, cart_items: list[dict],
                     delivery_address: str, payment_method: str,
                     special_instructions: str = None) -> dict:
        return self.orders.create_order(
            customer_id, cart_items, delivery_address, payment_method, special_instructions
        )

    def get_owner_orders(self, owner_user_id: int, actor_role: str,
                         status: str = None, limit: int = 50, offset: int = 0) -> list[dict]:
        owner = self.owners.get_owner_by_user(owner_user_id)
        return self.orders.get_owner_orders(owner["id"], owner_user_id, actor_role, status, limit, offset)

    def update_order_status(self, order_id: int, new_status: str,
                            actor_id: int, actor_role: str) -> dict:
        return self.orders.update_order_status(order_id, new_status, actor_id, actor_role)

    def register_account(self, *, full_name: str, email: str, password: str,
                         role: str = "customer", phone: str = None,
                         address: str = None, business_name: str = None,
                         license_number: str = None, city: str = None,
                         state: str = None, postal_code: str = None) -> dict:
        """
        Register a customer or owner account and persist the details in the DB.

        Owners get both a user row and a restaurant_owners row.
        """
        role = (role or "customer").strip().lower()
        if role not in ("customer", "owner"):
            raise ValidationError("Sign-up only supports customer or owner accounts.")

        user = self.users.register(email, password, full_name, role, phone, address)
        result = {"user": user, "owner": None}

        if role == "owner":
            try:
                owner = self.owners.register_owner(
                    user["id"],
                    business_name=business_name,
                    license_number=license_number,
                    phone=phone,
                    email=user["email"],
                    city=city,
                    state=state,
                    postal_code=postal_code,
                )
                result["owner"] = owner
            except Exception:
                try:
                    self.user_dao.delete_user(user["id"])
                except Exception:
                    log.exception("Failed to roll back partially created owner account.")
                raise

        return result
