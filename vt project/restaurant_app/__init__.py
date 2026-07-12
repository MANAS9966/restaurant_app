"""
restaurant_app package bootstrap.

Adds the package directory to sys.path so the existing absolute imports used
throughout the codebase continue to work when the project is imported from the
repository root.
"""
from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT_STR = str(PACKAGE_ROOT)

if PACKAGE_ROOT_STR not in sys.path:
    sys.path.insert(0, PACKAGE_ROOT_STR)

__all__ = ["PACKAGE_ROOT"]
