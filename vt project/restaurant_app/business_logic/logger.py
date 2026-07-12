"""
business_logic/logger.py
Centralized logging with rotating file handler + console output.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
LOG_FILE = os.path.join(LOG_DIR, "restaurant_app.log")

_configured = False


def get_logger(name: str = "restaurant_app") -> logging.Logger:
    """Return a configured logger. Safe to call multiple times."""
    global _configured
    logger = logging.getLogger(name)

    if not _configured:
        os.makedirs(LOG_DIR, exist_ok=True)
        logger.setLevel(logging.DEBUG)

        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # File handler (rotating, max 5 MB × 3 backups)
        fh = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=3,
                                 encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

        _configured = True

    return logger


# Module-level convenience logger
log = get_logger()
