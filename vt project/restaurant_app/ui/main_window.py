"""
restaurant_app/ui/main_window.py
Main window controller that shows login first and then routes to the role pages.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from restaurant_app.management import AppManager
from restaurant_app.ui.admin_tab import AdminTab
from restaurant_app.ui.common_widgets import Pill
from restaurant_app.ui.customer_tab import CustomerTab
from restaurant_app.ui.login_screen import LoginScreen
from restaurant_app.ui.owner_tab import OwnerTab
from restaurant_app.ui.signup_screen import SignupScreen
from restaurant_app.ui.styles import COLORS, apply_theme, toggle_theme


class RestaurantMainWindow:
    """Tkinter controller for the login flow and role-based pages."""

    def __init__(self, app_manager: AppManager | None = None):
        self.app = app_manager or AppManager().initialise()
        self.root = tk.Tk()
        self.root.title(self.app.app_name)
        width, height = self.app.config.window_size()
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(1200, 800)

        self.style = apply_theme(self.root)

        self.status_var = tk.StringVar(value="Ready")
        self.session = None
        self.current_user = None
        self.current_token = None

        self.root.bind("<Control-1>", lambda _e: self._show_role_tab("admin"))
        self.root.bind("<Control-2>", lambda _e: self._show_role_tab("owner"))
        self.root.bind("<Control-3>", lambda _e: self._show_role_tab("customer"))

        self.container = ttk.Frame(self.root, padding=18)
        self.container.pack(fill="both", expand=True)

        bottom_bar = ttk.Frame(self.root, style="Shell.TFrame")
        bottom_bar.pack(side="bottom", fill="x", padx=18, pady=(0, 10))

        self.status_bar = ttk.Label(bottom_bar, textvariable=self.status_var, anchor="w")
        self.status_bar.pack(side="left", fill="x", expand=True)

        self.theme_btn = ttk.Button(
            bottom_bar,
            text="☀️ Light Theme" if COLORS.is_dark else "🌙 Dark Theme",
            style="Ghost.TButton",
            command=self._toggle_theme,
        )
        self.theme_btn.pack(side="right")

        self.login_screen = LoginScreen(
            self.container,
            on_login=self._handle_login,
            on_demo_fill=self._fill_admin_demo,
            on_signup=self._show_signup,
        )
        self.login_screen.pack(fill="both", expand=True)

        self.signup_screen = None
        self.workspace = None
        self.notebook = None

    def _setup_style(self) -> None:
        # Theme is applied centrally in restaurant_app.ui.styles.apply_theme.
        return

    def _fill_admin_demo(self):
        return ("admin@gmail.com", "admin121")

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)
        if hasattr(self, "login_screen") and self.login_screen.winfo_exists():
            self.login_screen.set_message(message)
        if hasattr(self, "signup_screen") and self.signup_screen and self.signup_screen.winfo_exists():
            self.signup_screen.set_message(message)

    def _handle_login(self, email: str, password: str) -> None:
        result = self.app.login(email, password)
        if not result.get("success"):
            self._set_status(result.get("message") or result.get("error") or "Login failed")
            messagebox.showerror("Login failed", result.get("message") or result.get("error") or "Login failed")
            return

        self.session = result["data"]["session_token"]
        self.current_user = result["data"]["user"]
        self.current_token = self.session
        self._show_workspace()
        self._set_status(f"Logged in as {self.current_user['full_name']} - role: {self.current_user['role']}")

    def _clear_container(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

    def _show_login(self, message: str = None) -> None:
        self._clear_container()
        self.login_screen = LoginScreen(
            self.container,
            on_login=self._handle_login,
            on_demo_fill=self._fill_admin_demo,
            on_signup=self._show_signup,
        )
        self.login_screen.pack(fill="both", expand=True)
        self.signup_screen = None
        if message:
            self._set_status(message)

    def _show_signup(self) -> None:
        self._clear_container()
        self.signup_screen = SignupScreen(
            self.container,
            on_submit=self._handle_signup,
            on_back=lambda: self._show_login("Back to login"),
        )
        self.signup_screen.pack(fill="both", expand=True)
        self._set_status("Create a new account")

    def _handle_signup(self, payload: dict) -> None:
        if payload["password"] != payload["confirm_password"]:
            self._set_status("Passwords do not match")
            if self.signup_screen and self.signup_screen.winfo_exists():
                self.signup_screen.set_error("Password and confirmation do not match.")
            messagebox.showerror("Sign up failed", "Password and confirmation do not match.")
            return

        role = payload["role"]
        if role == "owner" and not payload["business_name"]:
            self._set_status("Owner business details are required")
            if self.signup_screen and self.signup_screen.winfo_exists():
                self.signup_screen.set_error("Business name is required for owner accounts.")
            messagebox.showerror("Sign up failed", "Business name is required for owner accounts.")
            return

        try:
            result = self.app.service.register_account(
                full_name=payload["full_name"],
                email=payload["email"],
                password=payload["password"],
                role=role,
                phone=payload["phone"],
                address=payload["address"],
                business_name=payload["business_name"],
                license_number=payload["license_number"],
                city=payload["city"],
                state=payload["state"],
                postal_code=payload["postal_code"],
            )
        except Exception as exc:
            self._set_status(str(exc))
            if self.signup_screen and self.signup_screen.winfo_exists():
                self.signup_screen.set_error(str(exc))
            messagebox.showerror("Sign up failed", str(exc))
            return

        user = result["user"]
        owner = result.get("owner")
        if owner:
            success_message = (
                f"Owner account created for {user['full_name']}. "
                f"Verification status: {owner.get('verification_status', 'pending')}."
            )
        else:
            success_message = f"Customer account created for {user['full_name']}."

        self._show_login(success_message)
        self.login_screen.email_var.set(user["email"])
        self._set_status(success_message)

    def _show_workspace(self) -> None:
        self._clear_container()

        top = ttk.Frame(self.container, style="Card.TFrame", padding=16)
        top.pack(fill="x", pady=(0, 14))
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=0)

        title_box = ttk.Frame(top, style="Card.TFrame")
        title_box.grid(row=0, column=0, sticky="w")
        ttk.Label(title_box, text=self.app.app_name, style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            title_box,
            text=f"Signed in as {self.current_user['full_name']} - role: {self.current_user['role']}",
            style="CardText.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        action_box = ttk.Frame(top, style="Card.TFrame")
        action_box.grid(row=0, column=1, sticky="e")
        Pill(action_box, text=self.current_user["role"].upper(), color=COLORS.accent).pack(
            side="left", padx=(0, 10)
        )
        ttk.Button(action_box, text="Logout", style="Ghost.TButton", command=self._logout).pack(side="left")

        self.workspace = ttk.Frame(self.container, style="App.TFrame")
        self.workspace.pack(fill="both", expand=True)

        notebook_card = ttk.Frame(self.workspace, style="Card.TFrame", padding=10)
        notebook_card.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(notebook_card)
        self.notebook.pack(fill="both", expand=True)

        role = self.current_user["role"]
        if role == "admin":
            self.admin_tab = AdminTab(self.notebook, self.app.service)
            self.notebook.add(self.admin_tab, text="Admin")
        elif role == "owner":
            self.owner_tab = OwnerTab(self.notebook, self.app.service, self.current_user)
            self.notebook.add(self.owner_tab, text="Owner")
        else:
            self.customer_tab = CustomerTab(self.notebook, self.app.service, self.current_user)
            self.notebook.add(self.customer_tab, text="Customer")

        self._show_role_tab(role)

    def _show_role_tab(self, role: str) -> None:
        if not self.notebook:
            return
        try:
            self.notebook.select(self.notebook.tabs()[0])
        except Exception:
            pass

    def _logout(self) -> None:
        if self.current_token:
            self.app.logout(self.current_token)
        self.session = None
        self.current_user = None
        self.current_token = None
        self._show_login("Logged out")
        self._set_status("Logged out")

    def _toggle_theme(self) -> None:
        toggle_theme(self.root)
        self.theme_btn.configure(text="☀️ Light Theme" if COLORS.is_dark else "🌙 Dark Theme")
        self._refresh_current_view()

    def _refresh_current_view(self) -> None:
        if hasattr(self, "login_screen") and self.login_screen and self.login_screen.winfo_exists():
            email = self.login_screen.email_var.get()
            msg = self.login_screen.message_var.get()
            self.login_screen.destroy()
            self.login_screen = LoginScreen(
                self.container,
                on_login=self._handle_login,
                on_demo_fill=self._fill_admin_demo,
                on_signup=self._show_signup,
            )
            self.login_screen.email_var.set(email)
            self.login_screen.message_var.set(msg)
            self.login_screen.pack(fill="both", expand=True)
        elif hasattr(self, "signup_screen") and self.signup_screen and self.signup_screen.winfo_exists():
            self.signup_screen.destroy()
            self.signup_screen = SignupScreen(
                self.container,
                on_submit=self._handle_signup,
                on_back=lambda: self._show_login("Back to login"),
            )
            self.signup_screen.pack(fill="both", expand=True)
        elif self.workspace and self.workspace.winfo_exists():
            self._show_workspace()

    def run(self) -> None:
        self.root.mainloop()
