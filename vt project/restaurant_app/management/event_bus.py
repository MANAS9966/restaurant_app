"""
management/event_bus.py
Lightweight publish/subscribe event bus for inter-layer communication.

Supported events:
  order.created, order.status_changed, order.cancelled
  user.registered, user.status_changed
  owner.verified, owner.rejected
  dish.created, dish.updated, dish.deleted
"""
from __future__ import annotations
import threading
from typing import Callable

_LOCK = threading.Lock()
_SUBSCRIBERS: dict[str, list[Callable]] = {}


def subscribe(event: str, handler: Callable) -> None:
    """Register *handler* to be called whenever *event* is published."""
    with _LOCK:
        _SUBSCRIBERS.setdefault(event, []).append(handler)


def unsubscribe(event: str, handler: Callable) -> None:
    """Remove a previously registered handler."""
    with _LOCK:
        if event in _SUBSCRIBERS:
            try:
                _SUBSCRIBERS[event].remove(handler)
            except ValueError:
                pass


def publish(event: str, **payload) -> None:
    """
    Fire all handlers registered for *event*.
    Handlers are called synchronously in registration order.
    Exceptions in handlers are swallowed to protect the publisher.
    """
    with _LOCK:
        handlers = list(_SUBSCRIBERS.get(event, []))

    for handler in handlers:
        try:
            handler(event=event, **payload)
        except Exception as exc:  # noqa: BLE001
            # Don't let a bad subscriber crash the app
            import logging
            logging.getLogger(__name__).error(
                "EventBus: handler %s raised for event '%s': %s",
                handler, event, exc
            )


def clear_all() -> None:
    """Remove all subscribers — useful in tests."""
    with _LOCK:
        _SUBSCRIBERS.clear()
