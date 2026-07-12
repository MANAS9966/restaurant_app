"""
Project entry point for the restaurant management system.
Bootstraps the application manager and launches the desktop display.
"""
from __future__ import annotations

import json
import sys

from restaurant_app.management import AppManager
from restaurant_app.ui.desktop_app import RestaurantDesktopApp


def main() -> int:
    app = AppManager().initialise()
    if "--seed-demo" in sys.argv:
        report = app.seed_demo_data()
        print(json.dumps(report, indent=2))
        return 0
    if "--cli" in sys.argv:
        summary = app.start()
        print(json.dumps(summary, indent=2))
        return 0

    try:
        RestaurantDesktopApp(app).run()
    except Exception:
        summary = app.start()
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
