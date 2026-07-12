"""
business_logic/owner_manager.py
Business logic for restaurant owner registration, verification, and analytics.
"""
from __future__ import annotations
import re

from business_logic.exceptions import (
    ValidationError, AuthorizationError, NotFoundError, DuplicateError
)
from business_logic.logger import log
from database.dao.owner_dao import OwnerDAO
from database.dao.user_dao import UserDAO
from database.dao.audit_dao import AuditDAO

LICENSE_RE = re.compile(r"^[A-Z0-9\-]{5,50}$", re.IGNORECASE)


class OwnerManager:

    def __init__(self, owner_dao: OwnerDAO, user_dao: UserDAO,
                 audit_dao: AuditDAO):
        self._owners = owner_dao
        self._users = user_dao
        self._audit = audit_dao

    # ---------------------------------------------------------------- create

    def register_owner(self, user_id: int, business_name: str,
                       license_number: str, phone: str = None,
                       email: str = None, city: str = None,
                       state: str = None, postal_code: str = None,
                       license_image_path: str = None) -> dict:
        """Create a restaurant-owner profile linked to an existing user."""
        user = self._users.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found.")
        if user["role"] != "owner":
            raise ValidationError("User must have 'owner' role to register as an owner.")

        if not business_name or not business_name.strip():
            raise ValidationError("Business name is required.")
        if not license_number or not LICENSE_RE.match(license_number.strip()):
            raise ValidationError(
                "License number must be 5–50 alphanumeric/hyphen characters."
            )

        if self._owners.get_owner_by_user_id(user_id):
            raise DuplicateError("An owner profile already exists for this user.")

        owner = self._owners.create_owner(
            user_id, business_name.strip(), license_number.strip().upper(),
            phone, email, city, state, postal_code, license_image_path
        )
        self._audit.log_operation(user_id, "OWNER_REGISTERED", "owner", owner["id"])
        log.info("Owner profile created for user %s: %s", user_id, business_name)
        return owner

    # ---------------------------------------------------------------- read

    def get_owner(self, owner_id: int) -> dict:
        owner = self._owners.get_owner_by_id(owner_id)
        if not owner:
            raise NotFoundError(f"Owner {owner_id} not found.")
        return owner

    def get_owner_by_user(self, user_id: int) -> dict:
        owner = self._owners.get_owner_by_user_id(user_id)
        if not owner:
            raise NotFoundError(f"No owner profile for user {user_id}.")
        return owner

    def get_all_owners(self, actor_role: str, filters: dict = None,
                       search: str = None, limit: int = 100,
                       offset: int = 0) -> list[dict]:
        if actor_role != "admin":
            raise AuthorizationError("Only admins can list all owners.")
        return self._owners.get_all_owners(filters, limit, offset, search)

    def get_analytics(self, actor_role: str, actor_user_id: int,
                      owner_id: int) -> dict:
        owner = self.get_owner(owner_id)
        if actor_role != "admin" and owner["user_id"] != actor_user_id:
            raise AuthorizationError("You can only view your own analytics.")
        return self._owners.get_owner_analytics(owner_id)

    # ---------------------------------------------------------------- update

    def update_owner(self, actor_role: str, actor_user_id: int,
                     owner_id: int, fields: dict) -> dict:
        owner = self.get_owner(owner_id)
        if actor_role != "admin" and owner["user_id"] != actor_user_id:
            raise AuthorizationError("You can only update your own profile.")

        allowed = {"business_name", "phone", "email", "city", "state",
                   "postal_code", "license_image_path"}
        invalid = set(fields.keys()) - allowed
        if invalid:
            raise ValidationError(f"Cannot update fields: {invalid}")

        self._owners.update_owner(owner_id, fields)
        self._audit.log_operation(
            actor_user_id, "OWNER_UPDATED", "owner", owner_id,
            old_value={k: owner.get(k) for k in fields},
            new_value=fields
        )
        return self.get_owner(owner_id)

    def verify_owner(self, actor_role: str, actor_user_id: int,
                     owner_id: int, approved: bool,
                     rejection_reason: str = None) -> dict:
        if actor_role != "admin":
            raise AuthorizationError("Only admins can verify owners.")
        self.get_owner(owner_id)  # raises NotFoundError if missing
        status = "verified" if approved else "rejected"
        self._owners.update_verification_status(
            owner_id, status, actor_user_id, rejection_reason
        )
        self._audit.log_operation(
            actor_user_id, f"OWNER_{status.upper()}", "owner", owner_id
        )
        log.info("Admin %s owner %s → %s", "approved" if approved else "rejected",
                 owner_id, status)
        return self.get_owner(owner_id)
