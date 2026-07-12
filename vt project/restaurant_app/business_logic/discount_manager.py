"""
business_logic/discount_manager.py
All discount validation and effective-price calculations.
"""
from __future__ import annotations
from business_logic.exceptions import DiscountError, NotFoundError
from database.dao.dish_dao import DishDAO
from database.dao.audit_dao import AuditDAO


class DiscountManager:

    def __init__(self, dish_dao: DishDAO, audit_dao: AuditDAO):
        self._dishes = dish_dao
        self._audit = audit_dao

    def validate_discount(self, dish_id: int, discount: float) -> bool:
        """Raise DiscountError if discount is invalid; return True otherwise."""
        if not (0 <= discount <= 100):
            raise DiscountError("Discount must be between 0 and 100 percent.")
        dish = self._dishes.get_dish_by_id(dish_id)
        if not dish:
            raise NotFoundError(f"Dish {dish_id} not found.")
        if discount > dish["max_discount_allowed"]:
            raise DiscountError(
                f"Discount {discount}% exceeds the maximum allowed "
                f"{dish['max_discount_allowed']}% for this dish."
            )
        return True

    def set_discount(self, actor_user_id: int, dish_id: int,
                     discount: float) -> dict:
        """Set discount and return updated price info."""
        self.validate_discount(dish_id, discount)
        dish = self._dishes.get_dish_by_id(dish_id)

        # Record price history
        self._audit.log_operation(
            actor_user_id, "DISCOUNT_CHANGED", "dish", dish_id,
            old_value={"discount": dish["current_discount"]},
            new_value={"discount": discount}
        )

        self._dishes.update_dish_discount(dish_id, discount)
        return self.get_effective_price(dish_id)

    def get_effective_price(self, dish_id: int) -> dict:
        """Return pricing breakdown for a dish."""
        dish = self._dishes.get_dish_by_id(dish_id)
        if not dish:
            raise NotFoundError(f"Dish {dish_id} not found.")
        original = round(dish["price"], 2)
        discount_pct = dish["current_discount"] or 0
        discount_amount = round(original * discount_pct / 100, 2)
        final = round(original - discount_amount, 2)
        return {
            "dish_id": dish_id,
            "original_price": original,
            "discount_percent": discount_pct,
            "discount_amount": discount_amount,
            "final_price": final,
            "max_discount_allowed": dish["max_discount_allowed"],
        }

    @staticmethod
    def calculate_final_price(original_price: float,
                              discount_percent: float) -> float:
        """Utility: compute final price from original + discount %."""
        return round(original_price * (1 - discount_percent / 100), 2)
