"""
restaurant_app/ui/login_screen.py
Branded login landing page with role-based sign-in.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from restaurant_app.ui.preferences import load_preferences, save_preferences
from restaurant_app.ui.styles import COLORS


class LoginScreen(ttk.Frame):
    """Professional login form with a left brand panel and right form card."""

    def __init__(self, parent, on_login, on_demo_fill=None, on_signup=None):
        super().__init__(parent, style="App.TFrame", padding=0)
        self.on_login = on_login
        self.on_demo_fill = on_demo_fill
        self.on_signup = on_signup

        prefs = load_preferences()
        remembered_email = prefs.get("remembered_email", "")

        self.email_var = tk.StringVar(value=remembered_email)
        self.password_var = tk.StringVar()
        self.message_var = tk.StringVar(value="Sign in to access your dashboard.")
        self.show_password_var = tk.BooleanVar(value=False)
        self.remember_var = tk.BooleanVar(value=bool(remembered_email))

        self._build_ui()

    def _build_ui(self) -> None:
        shell = ttk.Frame(self, style="App.TFrame", padding=24)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        self._build_brand_panel(shell)
        self._build_form_panel(shell)

    def _build_brand_panel(self, parent: ttk.Frame) -> None:
        brand = tk.Frame(parent, bg=COLORS.hero, padx=28, pady=28, highlightthickness=0)
        brand.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        brand.grid_propagate(False)

        title = tk.Label(
            brand,
            text="Restaurant Management System",
            bg=COLORS.hero,
            fg="#ffffff",
            font=("Segoe UI Semibold", 26),
            wraplength=420,
            justify="left",
        )
        title.pack(anchor="w")

        tk.Label(
            brand,
            text="A polished, role-aware Python desktop app for admin, owner, and customer workflows.",
            bg=COLORS.hero,
            fg="#f8fafc",
            font=("Segoe UI", 11),
            wraplength=430,
            justify="left",
        ).pack(anchor="w", pady=(12, 18))

        tk.Frame(brand, bg=COLORS.accent, height=4, width=120).pack(anchor="w", pady=(0, 18))

        for heading, body in [
            ("Admin access", "Monitor users, owners, orders, and system health from one place."),
            ("Owner workspace", "Manage dishes, discounts, and restaurant analytics with clarity."),
            ("Customer flow", "Create accounts, browse restaurants, and review orders easily."),
        ]:
            self._feature_block(brand, heading, body)

        tk.Label(
            brand,
            text="Tip: the default demo admin login is kept in lowercase for consistency.",
            bg=COLORS.hero,
            fg="#dbeafe",
            font=("Segoe UI", 9),
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(18, 0))

    def _feature_block(self, parent: tk.Widget, heading: str, body: str) -> None:
        row = tk.Frame(parent, bg=COLORS.hero, pady=0)
        row.pack(anchor="w", fill="x", pady=(0, 14))
        dot = tk.Canvas(row, width=12, height=12, bg=COLORS.hero, highlightthickness=0)
        dot.create_oval(2, 2, 10, 10, fill=COLORS.accent, outline=COLORS.accent)
        dot.pack(side="left", padx=(0, 10))
        text_box = tk.Frame(row, bg=COLORS.hero)
        text_box.pack(side="left", fill="x", expand=True)
        tk.Label(
            text_box,
            text=heading,
            bg=COLORS.hero,
            fg="#ffffff",
            font=("Segoe UI Semibold", 11),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            text_box,
            text=body,
            bg=COLORS.hero,
            fg="#e5eef8",
            font=("Segoe UI", 9),
            wraplength=400,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

    def _build_form_panel(self, parent: ttk.Frame) -> None:
        card_wrap = ttk.Frame(parent, style="App.TFrame")
        card_wrap.grid(row=0, column=1, sticky="nsew")
        card_wrap.rowconfigure(0, weight=1)
        card_wrap.columnconfigure(0, weight=1)

        card = ttk.Frame(card_wrap, style="Card.TFrame", padding=30)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)

        ttk.Label(card, text="Welcome back", style="Title.TLabel").pack(anchor="w")
        ttk.Label(card, text="Login", style="Section.TLabel").pack(anchor="w", pady=(4, 10))
        ttk.Label(card, textvariable=self.message_var, style="Muted.TLabel", wraplength=460).pack(
            anchor="w", pady=(0, 18)
        )

        self._field(card, "ID / Email", self.email_var)
        self._password_field(card, "Password", self.password_var)

        option_row = ttk.Frame(card, style="Card.TFrame")
        option_row.pack(fill="x", pady=(0, 8))
        ttk.Checkbutton(
            option_row,
            text="Show password",
            variable=self.show_password_var,
            command=self._toggle_password_visibility,
        ).pack(side="left")
        ttk.Checkbutton(
            option_row,
            text="Remember email",
            variable=self.remember_var,
        ).pack(side="right")

        button_row = ttk.Frame(card, style="Card.TFrame")
        button_row.pack(fill="x", pady=(10, 0))
        ttk.Button(button_row, text="Login", style="Accent.TButton", command=self._submit).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(
            button_row,
            text="Fill Demo",
            style="Ghost.TButton",
            command=self._fill_demo,
        ).pack(side="left", fill="x", expand=True, padx=(10, 0))

        if self.on_signup:
            ttk.Button(card, text="Create Account", style="Ghost.TButton", command=self.on_signup).pack(
                fill="x", pady=(10, 0)
            )

        ttk.Separator(card).pack(fill="x", pady=20)
        ttk.Label(
            card,
            text="Default demo credentials: admin@gmail.com / admin121",
            style="CardText.TLabel",
            wraplength=460,
        ).pack(anchor="w")

        self.after_idle(self.email_entry.focus_set)

    def _field(self, parent, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label, style="Field.TLabel").pack(anchor="w")
        entry = ttk.Entry(parent, textvariable=variable)
        entry.pack(fill="x", pady=(4, 12))
        if label == "ID / Email":
            self.email_entry = entry
            entry.bind("<Return>", lambda _event: self._submit())
        return entry

    def _password_field(self, parent, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label, style="Field.TLabel").pack(anchor="w")
        self.password_entry = ttk.Entry(parent, textvariable=variable, show="*")
        self.password_entry.pack(fill="x", pady=(4, 10))
        self.password_entry.bind("<Return>", lambda _event: self._submit())

    def _submit(self) -> None:
        email = self.email_var.get().strip().lower()
        password = self.password_var.get().strip().lower()
        if self.remember_var.get():
            save_preferences({"remembered_email": email})
        else:
            save_preferences({"remembered_email": ""})
        self.on_login(email, password)

    def _fill_demo(self) -> None:
        if self.on_demo_fill:
            email, password = self.on_demo_fill()
            self.email_var.set(email)
            self.password_var.set(password)
            self.remember_var.set(True)

    def set_message(self, message: str) -> None:
        self.message_var.set(message)

    def _toggle_password_visibility(self) -> None:
        self.password_entry.configure(show="" if self.show_password_var.get() else "*")
