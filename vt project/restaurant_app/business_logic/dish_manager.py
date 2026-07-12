"""
business_logic/dish_manager.py
Business logic for dish CRUD, ownership checks, and image handling.
"""
from __future__ import annotations
import os
import shutil

from business_logic.exceptions import (
    ValidationError, AuthorizationError, NotFoundError
)
from business_logic.discount_manager import DiscountManager
from business_logic.logger import log
from database.dao.dish_dao import DishDAO, VALID_CATEGORIES
from database.dao.owner_dao import OwnerDAO
from database.dao.audit_dao import AuditDAO

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "dishes")


class DishManager:

    def __init__(self, dish_dao: DishDAO, owner_dao: OwnerDAO,
                 audit_dao: AuditDAO, discount_manager: DiscountManager = None):
        self._dishes = dish_dao
        self._owners = owner_dao
        self._audit = audit_dao
        self._discount = discount_manager
        os.makedirs(IMAGES_DIR, exist_ok=True)

    # ---------------------------------------------------------------- helpers

    def _assert_owner(self, dish_id: int, actor_user_id: int,
                      actor_role: str) -> dict:
        """Raise AuthorizationError if actor doesn't own the dish."""
        dish = self._dishes.get_dish_by_id(dish_id)
        if not dish:
            raise NotFoundError(f"Dish {dish_id} not found.")
        if actor_role == "admin":
            return dish
        owner = self._owners.get_owner_by_user_id(actor_user_id)
        if not owner or owner["id"] != dish["owner_id"]:
            raise AuthorizationError("You do not own this dish.")
        return dish

    def _validate_dish_data(self, name: str, category: str, price: float,
                             description: str = None,
                             max_discount: float = None):
        if not name or len(name.strip()) > 100:
            raise ValidationError("Dish name is required and must be ≤ 100 characters.")
        if category not in VALID_CATEGORIES:
            raise ValidationError(
                f"Category must be one of: {', '.join(VALID_CATEGORIES)}"
            )
        if price is None or price < 0:
            raise ValidationError("Price must be a non-negative number.")
        if description and len(description) > 500:
            raise ValidationError("Description must be ≤ 500 characters.")
        if max_discount is not None and not (0 <= max_discount <= 100):
            raise ValidationError("Max discount must be between 0 and 100.")

    # ---------------------------------------------------------------- public API

    def create_dish(self, actor_user_id: int, actor_role: str,
                    name: str, category: str, price: float,
                    description: str = None, max_discount: float = 30,
                    image_path: str = None) -> dict:
        if actor_role not in ("owner", "admin"):
            raise AuthorizationError("Only owners and admins can create dishes.")

        owner = self._owners.get_owner_by_user_id(actor_user_id)
        if actor_role == "owner" and not owner:
            raise NotFoundError("No owner profile found for this user.")

        if actor_role == "owner" and owner["verification_status"] != "verified":
            raise AuthorizationError(
                "Your account must be verified before adding dishes."
            )

        self._validate_dish_data(name, category, price, description, max_discount)

        # Copy image to managed directory if provided
        stored_path = None
        if image_path and os.path.exists(image_path):
            ext = os.path.splitext(image_path)[1]
            stored_name = f"dish_{owner['id']}_{name[:20].replace(' ', '_')}{ext}"
            stored_path = os.path.join(IMAGES_DIR, stored_name)
            shutil.copy2(image_path, stored_path)

        dish = self._dishes.create_dish(
            owner["id"], name.strip(), category, round(price, 2),
            description, max_discount, stored_path
        )
        self._owners.update_total_dishes(owner["id"])
        self._audit.log_operation(actor_user_id, "DISH_CREATED", "dish", dish["id"],
                                  new_value={"name": name, "price": price})
        log.info("Dish created: %s (owner=%s)", name, owner["id"])
        return dish

    def get_dish(self, dish_id: int) -> dict:
        dish = self._dishes.get_dish_by_id(dish_id)
        if not dish:
            raise NotFoundError(f"Dish {dish_id} not found.")
        return dish

    def get_owner_dishes(self, actor_user_id: int, actor_role: str,
                         owner_user_id: int = None, filters: dict = None,
                         limit: int = 100, offset: int = 0) -> list[dict]:
        target_user = owner_user_id or actor_user_id
        if actor_role != "admin" and target_user != actor_user_id:
            raise AuthorizationError("You can only view your own dishes.")
        owner = self._owners.get_owner_by_user_id(target_user)
        if not owner:
            raise NotFoundError("No owner profile found.")
        return self._dishes.get_dishes_by_owner(owner["id"], filters, limit, offset)

    def get_all_dishes(self, search: str = None, category: str = None,
                       min_price: float = None, max_price: float = None,
                       owner_id: int = None, limit: int = 100,
                       offset: int = 0) -> list[dict]:
        """Customer-facing dish catalog."""
        if search or category or min_price is not None or max_price is not None or owner_id is not None:
            return self._dishes.search_dishes(
                search, category, min_price, max_price, owner_id=owner_id,
                limit=limit, offset=offset
            )
        return self._dishes.get_all_dishes(limit=limit, offset=offset)

    def update_dish(self, actor_user_id: int, actor_role: str,
                    dish_id: int, fields: dict) -> dict:
        dish = self._assert_owner(dish_id, actor_user_id, actor_role)

        allowed = {"name", "description", "category", "price",
                   "max_discount_allowed", "image_path"}
        invalid = set(fields.keys()) - allowed
        if invalid:
            raise ValidationError(f"Cannot update fields: {invalid}")

        if "name" in fields or "category" in fields or "price" in fields:
            self._validate_dish_data(
                fields.get("name", dish["name"]),
                fields.get("category", dish["category"]),
                fields.get("price", dish["price"]),
                fields.get("description", dish.get("description")),
                fields.get("max_discount_allowed", dish.get("max_discount_allowed"))
            )

        self._dishes.update_dish(dish_id, fields)
        self._audit.log_operation(actor_user_id, "DISH_UPDATED", "dish", dish_id,
                                  old_value={k: dish.get(k) for k in fields},
                                  new_value=fields)
        return self.get_dish(dish_id)

    def toggle_dish_status(self, actor_user_id: int, actor_role: str,
                           dish_id: int) -> dict:
        dish = self._assert_owner(dish_id, actor_user_id, actor_role)
        new_status = "inactive" if dish["status"] == "active" else "active"
        self._dishes.update_dish_status(dish_id, new_status)
        owner = self._owners.get_owner_by_user_id(actor_user_id)
        if owner:
            self._owners.update_total_dishes(owner["id"])
        return self.get_dish(dish_id)

    def delete_dish(self, actor_user_id: int, actor_role: str,
                    dish_id: int) -> bool:
        self._assert_owner(dish_id, actor_user_id, actor_role)
        if self._dishes.has_active_orders(dish_id):
            raise ValidationError(
                "Cannot delete a dish that has active (pending/in-progress) orders."
            )
        self._dishes.delete_dish(dish_id)
        owner = self._owners.get_owner_by_user_id(actor_user_id)
        if owner:
            self._owners.update_total_dishes(owner["id"])
        self._audit.log_operation(actor_user_id, "DISH_DELETED", "dish", dish_id)
        log.info("Dish %s deleted by user %s", dish_id, actor_user_id)
        return True

    def set_discount(self, actor_user_id: int, actor_role: str,
                     dish_id: int, discount: float) -> dict:
        self._assert_owner(dish_id, actor_user_id, actor_role)
        if not self._discount:
            raise ValidationError("Discount manager not configured.")
        return self._discount.set_discount(actor_user_id, dish_id, discount)

    def get_categories(self) -> list[str]:
        return VALID_CATEGORIES
