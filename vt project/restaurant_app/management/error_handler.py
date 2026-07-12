"""
management/error_handler.py
Maps application exceptions to safe, user-friendly messages and logs context.
"""
from __future__ import annotations
import logging
import traceback

from business_logic.exceptions import (
    RestaurantAppError, ValidationError, AuthenticationError,
    AuthorizationError, NotFoundError, DuplicateError,
    AccountLockedError, OrderStateError, DiscountError, DatabaseError
)

log = logging.getLogger("restaurant_app.errors")

# Map exception types → (title, user-friendly prefix)
_ERROR_MAP: dict[type, tuple[str, str]] = {
    ValidationError:     ("Validation Error",     ""),
    DuplicateError:      ("Duplicate Entry",      ""),
    AuthenticationError: ("Login Failed",         ""),
    AccountLockedError:  ("Account Locked",       ""),
    AuthorizationError:  ("Access Denied",        "You don't have permission: "),
    NotFoundError:       ("Not Found",            ""),
    OrderStateError:     ("Order Error",          ""),
    DiscountError:       ("Discount Error",       ""),
    DatabaseError:       ("Database Error",       "A database error occurred. Please try again."),
}


def handle(exc: Exception, context: str = "", user_id: int = None) -> dict:
    """
    Convert an exception into a standardised response dict and log it.

    Returns:
        {"success": False, "title": str, "message": str}
    """
    # Log full traceback at appropriate level
    if isinstance(exc, RestaurantAppError):
        log.warning(
            "[%s] user=%s — %s: %s",
            context, user_id or "?", type(exc).__name__, exc.message
        )
        title, prefix = _ERROR_MAP.get(type(exc), ("Error", ""))
        # Walk MRO for best match
        for klass, (t, p) in _ERROR_MAP.items():
            if isinstance(exc, klass):
                title, prefix = t, p
                break
        message = prefix + exc.message if prefix else exc.message
    else:
        log.error(
            "[%s] user=%s — Unexpected: %s\n%s",
            context, user_id or "?", exc,
            traceback.format_exc()
        )
        title = "Unexpected Error"
        message = "An unexpected error occurred. Please contact support."

    return {"success": False, "title": title, "message": message}


def safe_call(func, *args, context: str = "", user_id: int = None, **kwargs):
    """
    Call *func* and return its result, or an error dict on failure.
    Useful for UI callbacks that must never crash the event loop.
    """
    try:
        result = func(*args, **kwargs)
        return result
    except Exception as exc:  # noqa: BLE001
        return handle(exc, context=context, user_id=user_id)
