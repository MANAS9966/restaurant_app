"""
business_logic/exceptions.py
Custom exception hierarchy for the restaurant management system.
"""


class RestaurantAppError(Exception):
    """Base exception for all app-level errors."""
    def __init__(self, message: str, code: str = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__

    def to_dict(self) -> dict:
        return {"success": False, "error": self.message, "code": self.code}


class ValidationError(RestaurantAppError):
    """Raised when input fails validation."""


class AuthenticationError(RestaurantAppError):
    """Raised when login credentials are invalid."""


class AuthorizationError(RestaurantAppError):
    """Raised when a user lacks permission for an action."""


class NotFoundError(RestaurantAppError):
    """Raised when a requested resource does not exist."""


class DuplicateError(RestaurantAppError):
    """Raised when a unique constraint would be violated."""


class DatabaseError(RestaurantAppError):
    """Raised on unexpected database failures."""


class AccountLockedError(AuthenticationError):
    """Raised when a user account is locked due to too many failed logins."""


class OrderStateError(RestaurantAppError):
    """Raised when an invalid order status transition is attempted."""


class DiscountError(ValidationError):
    """Raised when a discount value is invalid or exceeds the allowed maximum."""
