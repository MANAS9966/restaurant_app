"""
restaurant_app/ui/styles.py
Shared Tkinter styling for the restaurant management UI.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class UIColors:
    def __init__(self, is_dark: bool = False):
        self.set_dark_mode(is_dark)

    def set_dark_mode(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        if is_dark:
            self.bg = "#121212"
            self.panel = "#1e1e1e"
            self.panel_alt = "#282828"
            self.text = "#e5e7eb"
            self.muted = "#9ca3af"
            self.heading = "#ffffff"
            self.border = "#374151"
            self.accent = "#df9a4f"
            self.accent_dark = "#c07c2f"
            self.accent_soft = "#3a2d1d"
            self.hero = "#0f172a"
            self.hero_soft = "#1e293b"
            self.success = "#22c55e"
            self.danger = "#ef4444"
            self.info = "#38bdf8"
        else:
            self.bg = "#f5f1e8"
            self.panel = "#ffffff"
            self.panel_alt = "#fbf7f0"
            self.text = "#1f2937"
            self.muted = "#6b7280"
            self.heading = "#0f172a"
            self.border = "#e5dccd"
            self.accent = "#c07c2f"
            self.accent_dark = "#9a5f14"
            self.accent_soft = "#f6e7d1"
            self.hero = "#111827"
            self.hero_soft = "#1f2937"
            self.success = "#15803d"
            self.danger = "#b91c1c"
            self.info = "#0369a1"


def get_initial_theme() -> bool:
    """Read the initial theme from local preferences or fallback to config default."""
    try:
        from restaurant_app.ui.preferences import load_preferences
        prefs = load_preferences()
        if "theme" in prefs:
            return prefs["theme"] == "dark"
    except Exception:
        pass

    try:
        from restaurant_app.management.config_manager import ConfigManager
        cfg = ConfigManager()
        return cfg.get("app", "default_theme", default="dark") == "dark"
    except Exception:
        pass

    return True


COLORS = UIColors(is_dark=get_initial_theme())


def toggle_theme(root: tk.Tk | tk.Toplevel) -> None:
    """Toggle the global theme mode and save to preferences."""
    is_dark = not COLORS.is_dark
    COLORS.set_dark_mode(is_dark)

    try:
        from restaurant_app.ui.preferences import load_preferences, save_preferences
        prefs = load_preferences()
        prefs["theme"] = "dark" if is_dark else "light"
        save_preferences(prefs)
    except Exception:
        pass

    apply_theme(root)


def apply_theme(root: tk.Tk | tk.Toplevel) -> ttk.Style:
    """Apply the shared UI theme to a Tk root or toplevel window."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=COLORS.bg)

    # Frame styles
    style.configure("App.TFrame", background=COLORS.bg)
    style.configure("Shell.TFrame", background=COLORS.bg)
    style.configure("Card.TFrame", background=COLORS.panel, relief="solid", borderwidth=1, bordercolor=COLORS.border, lightcolor=COLORS.border, darkcolor=COLORS.border)
    style.configure("AltCard.TFrame", background=COLORS.panel_alt, relief="solid", borderwidth=1, bordercolor=COLORS.border, lightcolor=COLORS.border, darkcolor=COLORS.border)
    style.configure("Hero.TFrame", background=COLORS.hero)
    style.configure("HeroAccent.TFrame", background=COLORS.hero_soft)
    style.configure("Section.TFrame", background=COLORS.panel)

    style.configure("TFrame", background=COLORS.bg)
    
    # Label styles
    style.configure("TLabel", background=COLORS.bg, foreground=COLORS.text, font=("Segoe UI", 10))
    style.configure("Title.TLabel", background=COLORS.bg, foreground=COLORS.heading, font=("Segoe UI Semibold", 24))
    style.configure("Section.TLabel", background=COLORS.bg, foreground=COLORS.heading, font=("Segoe UI Semibold", 14))
    style.configure("Heading.TLabel", background=COLORS.bg, foreground=COLORS.heading, font=("Segoe UI Semibold", 18))
    style.configure("Body.TLabel", background=COLORS.bg, foreground=COLORS.text, font=("Segoe UI", 10))
    style.configure("Muted.TLabel", background=COLORS.bg, foreground=COLORS.muted, font=("Segoe UI", 9))
    style.configure("Field.TLabel", background=COLORS.panel, foreground=COLORS.text, font=("Segoe UI Semibold", 10))
    style.configure("CardTitle.TLabel", background=COLORS.panel, foreground=COLORS.heading, font=("Segoe UI Semibold", 12))
    style.configure("CardText.TLabel", background=COLORS.panel, foreground=COLORS.muted, font=("Segoe UI", 9))
    style.configure("Stat.TLabel", background=COLORS.panel, foreground=COLORS.heading, font=("Segoe UI Semibold", 20))
    style.configure("HeroTitle.TLabel", background=COLORS.hero, foreground="#ffffff", font=("Segoe UI Semibold", 24))
    style.configure("HeroText.TLabel", background=COLORS.hero, foreground="#f8fafc", font=("Segoe UI", 10))
    style.configure("HeroSmall.TLabel", background=COLORS.hero, foreground="#f8fafc", font=("Segoe UI Semibold", 9))
    
    # Entry styles
    style.configure("TEntry", fieldbackground=COLORS.panel, foreground=COLORS.text, bordercolor=COLORS.border, lightcolor=COLORS.border, darkcolor=COLORS.border, insertcolor=COLORS.text, padding=6)
    
    # Combobox styles
    style.configure("TCombobox", fieldbackground=COLORS.panel, foreground=COLORS.text, background=COLORS.bg, bordercolor=COLORS.border, lightcolor=COLORS.border, darkcolor=COLORS.border, arrowcolor=COLORS.text, padding=6)
    style.map("TCombobox", fieldbackground=[("readonly", COLORS.panel)], foreground=[("readonly", COLORS.text)])

    # Labelframe styles
    style.configure("TLabelframe", background=COLORS.panel, bordercolor=COLORS.border, lightcolor=COLORS.border, darkcolor=COLORS.border)
    style.configure("TLabelframe.Label", background=COLORS.panel, foreground=COLORS.heading, font=("Segoe UI Semibold", 10))

    # Checkbutton styles
    style.configure("TCheckbutton", background=COLORS.panel, foreground=COLORS.text, focuscolor=COLORS.panel)
    style.map("TCheckbutton", background=[("active", COLORS.panel_alt)], foreground=[("active", COLORS.text)])

    # Panedwindow styles
    style.configure("TPanedwindow", background=COLORS.bg)
    style.configure("Sash", background=COLORS.border, sashthickness=4)

    # Scrollbar styles
    style.configure("TScrollbar", gripcount=0, background=COLORS.panel_alt, bordercolor=COLORS.border, lightcolor=COLORS.border, darkcolor=COLORS.border, arrowcolor=COLORS.text, troughcolor=COLORS.bg)
    style.map("TScrollbar", background=[("active", COLORS.border), ("pressed", COLORS.accent)])

    # Treeview styles
    style.configure("Treeview", background=COLORS.panel, fieldbackground=COLORS.panel, foreground=COLORS.text, bordercolor=COLORS.border, lightcolor=COLORS.border, darkcolor=COLORS.border, font=("Segoe UI", 10))
    style.configure("Treeview.Heading", background=COLORS.panel_alt, foreground=COLORS.heading, bordercolor=COLORS.border, lightcolor=COLORS.border, darkcolor=COLORS.border, font=("Segoe UI Semibold", 10))
    style.map("Treeview", background=[("selected", COLORS.accent)], foreground=[("selected", "#ffffff")])
    style.map("Treeview.Heading", background=[("active", COLORS.border)])

    # Button styles
    style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=(14, 8), bordercolor=COLORS.border, lightcolor=COLORS.border, darkcolor=COLORS.border)
    style.configure("Ghost.TButton", font=("Segoe UI Semibold", 10), padding=(14, 8), bordercolor=COLORS.border, lightcolor=COLORS.border, darkcolor=COLORS.border)
    style.configure("Danger.TButton", font=("Segoe UI Semibold", 10), padding=(14, 8), bordercolor=COLORS.border, lightcolor=COLORS.border, darkcolor=COLORS.border)
    
    style.configure("TNotebook", background=COLORS.bg, borderwidth=0)
    style.configure("TNotebook.Tab", padding=(16, 10), font=("Segoe UI Semibold", 10))
    
    style.map(
        "Accent.TButton",
        background=[("active", COLORS.accent_dark), ("!active", COLORS.accent)],
        foreground=[("!disabled", "#ffffff")],
        relief=[("pressed", "sunken"), ("!pressed", "raised")],
    )
    style.map(
        "Ghost.TButton",
        background=[("active", COLORS.panel_alt), ("!active", COLORS.panel)],
        foreground=[("!disabled", COLORS.text)],
    )
    style.map(
        "Danger.TButton",
        background=[("active", "#991b1b"), ("!active", COLORS.danger)],
        foreground=[("!disabled", "#ffffff")],
    )
    style.map("TNotebook.Tab", background=[("selected", COLORS.panel), ("!selected", COLORS.bg)], foreground=[("selected", COLORS.heading), ("!selected", COLORS.muted)])
    
    # Separator style
    style.configure("TSeparator", background=COLORS.border)

    return style


