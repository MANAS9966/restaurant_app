"""
business_logic/auth.py
Password hashing, RBAC decorator, and permission checker.
"""
from __future__ import annotations
import functools
from business_logic.exceptions import AuthorizationError

# Try bcrypt; fall back to hashlib for environments without it
try:
    import bcrypt
    _USE_BCRYPT = True
except ImportError:
    import hashlib, os
    _USE_BCRYPT = False


# ------------------------------------------------------------------ hashing

def hash_password(plain: str) -> str:
    """Return a hashed password string ready for DB storage."""
    plain = plain.strip().lower()
    if _USE_BCRYPT:
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
    # Fallback: sha256 with random salt prefix
    salt = os.urandom(16).hex()
    digest = hashlib.sha256((salt + plain).encode()).hexdigest()
    return f"sha256${salt}${digest}"


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored hash."""
    plain = plain.strip().lower()
    if _USE_BCRYPT and not hashed.startswith("sha256$"):
        try:
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        except Exception:
            return False
    # Fallback sha256 check
    try:
        _, salt, digest = hashed.split("$", 2)
        return hashlib.sha256((salt + plain).encode()).hexdigest() == digest
    except Exception:
        return False


# ------------------------------------------------------------------ RBAC

# Role hierarchy: each role includes the permissions listed for it
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "view_all_users", "manage_users", "view_all_owners",
        "manage_owners", "verify_owners", "view_all_orders",
        "manage_all_orders", "view_audit_log", "view_sessions",
        "force_logout", "view_all_dishes"
    },
    "owner": {
        "manage_own_dishes", "view_own_orders",
        "update_order_status", "view_own_analytics"
    },
    "customer": {
        "browse_restaurants", "browse_dishes",
        "create_order", "view_own_orders", "cancel_own_order"
    },
}


def check_permission(user_role: str, permission: str) -> bool:
    """Return True if the role has the given permission."""
    return permission in ROLE_PERMISSIONS.get(user_role, set())


def require_permission(permission: str):
    """Decorator that checks role-based permission on a manager method.

    The decorated method must receive `user_role` as its first keyword
    argument (after self).

    Usage::

        @require_permission("manage_users")
        def deactivate_user(self, actor_role, user_id): ...
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            # Convention: first positional arg is actor_role
            role = args[0] if args else kwargs.get("actor_role", "")
            if not check_permission(role, permission):
                raise AuthorizationError(
                    f"Role '{role}' is not allowed to perform '{permission}'"
                )
            return fn(self, *args, **kwargs)
        return wrapper
    return decorator
