"""
restaurant_app/ui/preferences.py
Tiny local preferences store used for UI convenience features.
"""
from __future__ import annotations

import json
from pathlib import Path


PREFS_PATH = Path.home() / ".restaurant_app_prefs.json"


def load_preferences() -> dict:
    if not PREFS_PATH.exists():
        return {}
    try:
        return json.loads(PREFS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_preferences(prefs: dict) -> None:
    try:
        PREFS_PATH.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
    except Exception:
        pass

