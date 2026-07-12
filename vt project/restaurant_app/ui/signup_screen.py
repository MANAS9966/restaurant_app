"""
restaurant_app/ui/signup_screen.py
Account creation screen for customer and owner roles.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from restaurant_app.ui.styles import COLORS


class SignupScreen(ttk.Frame):
    """Role-aware sign-up page with a polished two-column layout."""

    def __init__(self, parent, on_submit, on_back):
        super().__init__(parent, style="App.TFrame", padding=0)
        self.on_submit = on_submit
        self.on_back = on_back

        self.full_name_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.confirm_password_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.address_var = tk.StringVar()
        self.role_var = tk.StringVar(value="customer")
        self.business_name_var = tk.StringVar()
        self.license_number_var = tk.StringVar()
        self.city_var = tk.StringVar()
        self.state_var = tk.StringVar()
        self.postal_code_var = tk.StringVar()
        self.message_var = tk.StringVar(value="Create a customer or owner account.")
        self.show_password_var = tk.BooleanVar(value=False)

        self._build_ui()
        self._toggle_owner_fields()
        self._toggle_password_visibility()

    def _build_ui(self) -> None:
        shell = ttk.Frame(self, style="App.TFrame", padding=24)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.columnconfigure(1, weight=1)

        self._build_brand_panel(shell)
        self._build_form_panel(shell)

    def _build_brand_panel(self, parent: ttk.Frame) -> None:
        brand = tk.Frame(parent, bg=COLORS.hero, padx=28, pady=28)
        brand.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        brand.grid_propagate(False)

        tk.Label(
            brand,
            text="Create your account",
            bg=COLORS.hero,
            fg="#ffffff",
            font=("Segoe UI Semibold", 26),
            anchor="w",
            justify="left",
        ).pack(anchor="w")
        tk.Label(
            brand,
            text="A clean onboarding flow for customers and restaurant owners.",
            bg=COLORS.hero,
            fg="#f8fafc",
            font=("Segoe UI", 11),
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(12, 18))
        tk.Frame(brand, bg=COLORS.accent, height=4, width=120).pack(anchor="w", pady=(0, 18))

        for heading, body in [
            ("Customer account", "Browse restaurants, place orders, and track your history."),
            ("Owner account", "Create a storefront profile and add dishes after verification."),
            ("Lowercase login", "ID and password are normalized to lowercase for simple sign-in."),
        ]:
            self._feature_block(brand, heading, body)

    def _feature_block(self, parent: tk.Widget, heading: str, body: str) -> None:
        row = tk.Frame(parent, bg=COLORS.hero)
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
        wrap = ttk.Frame(parent, style="App.TFrame")
        wrap.grid(row=0, column=1, sticky="nsew")
        wrap.columnconfigure(0, weight=1)

        card = ttk.Frame(wrap, style="Card.TFrame", padding=30)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="Sign up", style="Title.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=self.message_var, style="Muted.TLabel", wraplength=520).pack(
            anchor="w", pady=(6, 16)
        )

        form = ttk.Frame(card, style="Card.TFrame")
        form.pack(fill="both", expand=True)

        self._field(form, "Full Name", self.full_name_var)
        self._field(form, "ID / Email", self.email_var)
        self._field(form, "Phone", self.phone_var)
        self._field(form, "Address", self.address_var)

        ttk.Label(form, text="Role", style="Field.TLabel").pack(anchor="w")
        self.role_combo = ttk.Combobox(
            form, textvariable=self.role_var, values=("customer", "owner"), state="readonly"
        )
        self.role_combo.pack(fill="x", pady=(4, 12))
        self.role_combo.bind("<<ComboboxSelected>>", lambda _e: self._toggle_owner_fields())

        self._password_field(form, "Password", self.password_var)
        self._password_field(form, "Confirm Password", self.confirm_password_var)

        options = ttk.Frame(form, style="Card.TFrame")
        options.pack(fill="x", pady=(0, 10))
        ttk.Checkbutton(
            options,
            text="Show password",
            variable=self.show_password_var,
            command=self._toggle_password_visibility,
        ).pack(side="left")
        self.notice_var = tk.StringVar(value="Owner sign-up requires business details.")
        ttk.Label(options, textvariable=self.notice_var, style="CardText.TLabel").pack(side="right")

        self.owner_frame = ttk.Labelframe(form, text="Owner Details", padding=12)
        self._field(self.owner_frame, "Business Name", self.business_name_var)
        self._field(self.owner_frame, "License Number", self.license_number_var)
        self._field(self.owner_frame, "City", self.city_var)
        self._field(self.owner_frame, "State", self.state_var)
        self._field(self.owner_frame, "Postal Code", self.postal_code_var)

        button_row = ttk.Frame(form, style="Card.TFrame")
        button_row.pack(fill="x", pady=(12, 0))
        ttk.Button(button_row, text="Create Account", style="Accent.TButton", command=self._submit).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(button_row, text="Back to Login", style="Ghost.TButton", command=self.on_back).pack(
            side="left", fill="x", expand=True, padx=(10, 0)
        )

        self.after_idle(self.full_name_entry.focus_set)

    def _field(self, parent, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label, style="Field.TLabel").pack(anchor="w")
        entry = ttk.Entry(parent, textvariable=variable)
        entry.pack(fill="x", pady=(4, 12))
        if label == "Full Name":
            self.full_name_entry = entry
        entry.bind("<Return>", lambda _event: self._submit())
        return entry

    def _password_field(self, parent, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label, style="Field.TLabel").pack(anchor="w")
        entry = ttk.Entry(parent, textvariable=variable, show="*")
        entry.pack(fill="x", pady=(4, 12))
        if label == "Password":
            self.password_entry = entry
        else:
            self.confirm_password_entry = entry
        entry.bind("<Return>", lambda _event: self._submit())

    def _toggle_owner_fields(self) -> None:
        if self.role_var.get() == "owner":
            if not self.owner_frame.winfo_ismapped():
                self.owner_frame.pack(fill="x", pady=(0, 12))
            self.notice_var.set("Owner accounts start as pending verification.")
        else:
            self.owner_frame.pack_forget()
            self.notice_var.set("Customer accounts go live immediately.")

    def _toggle_password_visibility(self) -> None:
        show = "" if self.show_password_var.get() else "*"
        self.password_entry.configure(show=show)
        self.confirm_password_entry.configure(show=show)

    def _submit(self) -> None:
        payload = {
            "full_name": self.full_name_var.get().strip(),
            "email": self.email_var.get().strip().lower(),
            "password": self.password_var.get().strip().lower(),
            "confirm_password": self.confirm_password_var.get().strip().lower(),
            "role": self.role_var.get().strip().lower(),
            "phone": self.phone_var.get().strip() or None,
            "address": self.address_var.get().strip() or None,
            "business_name": self.business_name_var.get().strip() or None,
            "license_number": self.license_number_var.get().strip() or None,
            "city": self.city_var.get().strip() or None,
            "state": self.state_var.get().strip() or None,
            "postal_code": self.postal_code_var.get().strip() or None,
        }
        self.on_submit(payload)

    def set_error(self, message: str) -> None:
        """Show a validation or database error on the page itself."""
        self.message_var.set(message)

    def set_message(self, message: str) -> None:
        self.message_var.set(message)

    def reset(self, preserve_role: bool = True) -> None:
        """Clear the form after a successful signup."""
        self.full_name_var.set("")
        self.email_var.set("")
        self.password_var.set("")
        self.confirm_password_var.set("")
        self.phone_var.set("")
        self.address_var.set("")
        self.business_name_var.set("")
        self.license_number_var.set("")
        self.city_var.set("")
        self.state_var.set("")
        self.postal_code_var.set("")
        self.show_password_var.set(False)
        if not preserve_role:
            self.role_var.set("customer")
        self._toggle_owner_fields()
        self._toggle_password_visibility()
