"""
business_logic/user_manager.py
All user-related business operations.
"""
from __future__ import annotations
import re
from datetime import datetime, timedelta, timezone

from business_logic.exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    NotFoundError, DuplicateError, AccountLockedError
)
from business_logic.auth import hash_password, verify_password, require_permission
from business_logic.logger import log
from database.dao.user_dao import UserDAO
from database.dao.audit_dao import AuditDAO

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _sqlite_timestamp(dt: datetime) -> str:
    """Format datetimes for SQLite TIMESTAMP columns."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


class UserManager:
    """Business logic for user registration, login, and profile management."""

    MAX_ATTEMPTS = 5
    LOCKOUT_MINUTES = 30

    def __init__(self, user_dao: UserDAO, audit_dao: AuditDAO,
                 password_min_length: int = 8):
        self._users = user_dao
        self._audit = audit_dao
        self._pw_min = password_min_length

    # ---------------------------------------------------------------- validation

    def _validate_email(self, email: str):
        if not email or not EMAIL_RE.match(email):
            raise ValidationError("Invalid email address format.")

    def _validate_password(self, password: str):
        if len(password) < self._pw_min:
            raise ValidationError(
                f"Password must be at least {self._pw_min} characters."
            )
        if not re.search(r"[0-9]", password):
            raise ValidationError("Password must contain at least one digit.")

    # ---------------------------------------------------------------- public API

    def register(self, email: str, password: str, full_name: str,
                 role: str = "customer", phone: str = None,
                 address: str = None) -> dict:
        """Register a new user. Returns the created user dict."""
        email = email.strip().lower()
        password = password.strip().lower()
        self._validate_email(email)
        self._validate_password(password)
        if not full_name or not full_name.strip():
            raise ValidationError("Full name is required.")
        if role not in ("admin", "owner", "customer"):
            raise ValidationError(f"Invalid role: {role}")

        if self._users.get_user_by_email(email):
            raise DuplicateError("An account with this email already exists.")

        pw_hash = hash_password(password)
        user = self._users.create_user(email, pw_hash, full_name.strip(),
                                       role, phone, address)
        self._audit.log_operation(user["id"], "USER_REGISTERED",
                                  "user", user["id"],
                                  new_value={"email": email, "role": role})
        log.info("User registered: %s (role=%s)", email, role)
        return _safe_user(user)

    def login(self, email: str, password: str) -> dict:
        """Validate credentials. Returns user dict on success."""
        email = email.strip().lower()
        password_raw = password.strip()
        password = password_raw.lower()
        user = self._users.get_user_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password.")

        # Check account status
        if user["status"] == "inactive":
            raise AuthenticationError("This account has been deactivated.")

        # Check lock
        if user["locked_until"]:
            locked_until = _parse_dt(user["locked_until"])
            if locked_until and _utcnow() < locked_until:
                mins = int((locked_until - _utcnow()).total_seconds() / 60) + 1
                raise AccountLockedError(
                    f"Account is locked. Try again in {mins} minute(s)."
                )
            else:
                # Lock has expired — reset attempts
                self._users.update_login_attempt(user["id"], reset=True)
                user = self._users.get_user_by_id(user["id"])

        if user["status"] == "locked" and not user["locked_until"]:
            raise AccountLockedError("Account is locked. Contact an administrator.")

        if not (verify_password(password, user["password_hash"]) or
                verify_password(password_raw, user["password_hash"])):
            attempts = (user["failed_login_attempts"] or 0) + 1
            locked_until = None
            if attempts >= self.MAX_ATTEMPTS:
                locked_until = _sqlite_timestamp(
                    _utcnow() + timedelta(minutes=self.LOCKOUT_MINUTES)
                )
                self._users.update_user_status(user["id"], "locked")
                self._users.update_login_attempt(user["id"], locked_until=locked_until)
                raise AccountLockedError(
                    f"Too many failed attempts. Account locked for "
                    f"{self.LOCKOUT_MINUTES} minutes."
                )
            self._users.update_login_attempt(user["id"])
            raise AuthenticationError(
                f"Invalid email or password. "
                f"{self.MAX_ATTEMPTS - attempts} attempt(s) remaining."
            )

        # Successful login — reset attempts
        self._users.update_login_attempt(user["id"], reset=True)
        if user["status"] == "locked":
            self._users.update_user_status(user["id"], "active")

        self._audit.log_operation(user["id"], "USER_LOGIN", "user", user["id"])
        log.info("User logged in: %s", email)
        return _safe_user(self._users.get_user_by_id(user["id"]))

    def get_user(self, user_id: int) -> dict:
        user = self._users.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found.")
        return _safe_user(user)

    def get_all_users(self, actor_role: str, filters: dict = None,
                      search: str = None, limit: int = 100,
                      offset: int = 0) -> list[dict]:
        if actor_role != "admin":
            raise AuthorizationError("Only admins can list all users.")
        users = self._users.get_all_users(filters, limit, offset, search)
        return [_safe_user(u) for u in users]

    def update_user(self, actor_id: int, actor_role: str,
                    target_id: int, fields: dict) -> dict:
        """Update user profile fields. Owners/customers can only update themselves."""
        if actor_role != "admin" and actor_id != target_id:
            raise AuthorizationError("You can only update your own profile.")
        user = self._users.get_user_by_id(target_id)
        if not user:
            raise NotFoundError(f"User {target_id} not found.")

        allowed = {"full_name", "phone", "address"}
        if actor_role == "admin":
            allowed.add("role")
        invalid = set(fields.keys()) - allowed
        if invalid:
            raise ValidationError(f"Cannot update fields: {invalid}")

        if "email" in fields:
            self._validate_email(fields["email"])

        self._users.update_user(target_id, fields)
        self._audit.log_operation(actor_id, "USER_UPDATED", "user", target_id,
                                  old_value=_safe_user(user), new_value=fields)
        return self.get_user(target_id)

    def set_user_status(self, actor_role: str, target_id: int, status: str) -> dict:
        """Admin-only: activate, deactivate, or lock a user."""
        if actor_role != "admin":
            raise AuthorizationError("Only admins can change user status.")
        if status not in ("active", "inactive", "locked"):
            raise ValidationError(f"Invalid status: {status}")
        user = self._users.get_user_by_id(target_id)
        if not user:
            raise NotFoundError(f"User {target_id} not found.")
        self._users.update_user_status(target_id, status)
        log.info("Admin set user %s status → %s", target_id, status)
        return self.get_user(target_id)

    def delete_user(self, actor_role: str, target_id: int) -> bool:
        if actor_role != "admin":
            raise AuthorizationError("Only admins can delete users.")
        user = self._users.get_user_by_id(target_id)
        if not user:
            raise NotFoundError(f"User {target_id} not found.")
        self._users.delete_user(target_id)
        log.warning("Admin deleted user %s (%s)", target_id, user["email"])
        return True

    def count_by_role(self) -> dict:
        return self._users.get_all_user_count_by_role()


# ------------------------------------------------------------------ helpers

def _safe_user(user: dict) -> dict:
    """Return user dict without sensitive fields."""
    safe = dict(user)
    safe.pop("password_hash", None)
    safe.pop("failed_login_attempts", None)
    safe.pop("locked_until", None)
    return safe


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except Exception:
        return None
