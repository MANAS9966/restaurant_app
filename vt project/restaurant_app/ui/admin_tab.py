"""
restaurant_app/ui/admin_tab.py
Admin dashboard with users, owners, and high level metrics.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from restaurant_app.ui.common_widgets import MetricCard, SearchableTable, SectionHeader


class AdminTab(ttk.Frame):
    """Admin workspace."""

    def __init__(self, parent, service):
        super().__init__(parent, padding=16)
        self.service = service
        self.user_count_var = tk.StringVar(value="0")
        self.owner_count_var = tk.StringVar(value="0")
        self.dish_count_var = tk.StringVar(value="0")
        self.order_count_var = tk.StringVar(value="0")
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        header = SectionHeader(
            self,
            "Admin Dashboard",
            "Manage users, restaurant owners, and overall system state from a single view.",
            action_text="Refresh",
            action_command=self.refresh,
        )
        header.pack(fill="x")

        cards = ttk.Frame(self)
        cards.pack(fill="x", pady=(16, 16))
        card_specs = [
            ("Users", self.user_count_var, "Registered accounts"),
            ("Owners", self.owner_count_var, "Restaurant profiles"),
            ("Dishes", self.dish_count_var, "Menu items"),
            ("Orders", self.order_count_var, "Sales records"),
        ]
        for idx, (label, var, hint) in enumerate(
            card_specs
        ):
            card = MetricCard(cards, label, var, hint=hint, card_type=label)
            card.grid(row=0, column=idx, sticky="nsew", padx=(0 if idx == 0 else 12, 0))
            cards.columnconfigure(idx, weight=1)

        tables = ttk.Notebook(self)
        tables.pack(fill="both", expand=True)

        users_frame = SearchableTable(
            tables,
            title="Users",
            columns=["ID", "Name", "Email", "Role", "Status"],
            subtitle="Search by name, email, role, or status.",
            search_hint="Search users",
        )
        owners_frame = SearchableTable(
            tables,
            title="Restaurant Owners",
            columns=["ID", "Business", "Owner", "Status", "Rating"],
            subtitle="Search by business name, owner, verification status, or rating.",
            search_hint="Search owners",
        )
        tables.add(users_frame, text="Users")
        tables.add(owners_frame, text="Restaurant Owners")

        self.users_table = users_frame
        self.owners_table = owners_frame

        action_row = ttk.Frame(self)
        action_row.pack(fill="x", pady=(12, 0))
        ttk.Button(action_row, text="Suspend User", style="Danger.TButton", command=self._suspend_selected_user).pack(
            side="left"
        )
        ttk.Button(action_row, text="Reactivate User", style="Accent.TButton", command=self._activate_selected_user).pack(
            side="left", padx=(10, 0)
        )
        ttk.Button(action_row, text="Refresh", style="Ghost.TButton", command=self.refresh).pack(
            side="right"
        )

    def _selected_user_id(self) -> int | None:
        row = self.users_table.get_selected_row()
        if not row:
            return None
        try:
            return int(row[0])
        except Exception:
            return None

    def _suspend_selected_user(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            messagebox.showinfo("Admin", "Select a user first.")
            return
        try:
            self.service.set_user_status("admin", user_id, "inactive")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Admin", str(exc))

    def _activate_selected_user(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            messagebox.showinfo("Admin", "Select a user first.")
            return
        try:
            self.service.set_user_status("admin", user_id, "active")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Admin", str(exc))

    def refresh(self) -> None:
        self.user_count_var.set(str(self.service.user_dao.count_users()))
        self.owner_count_var.set(str(self.service.owner_dao.count_owners()))
        self.dish_count_var.set(str(self.service.dish_dao.count_dishes()))
        self.order_count_var.set(str(self.service.order_dao.count_orders()))

        users_rows = [
            (user["id"], user["full_name"], user["email"], user["role"], user["status"])
            for user in self.service.users.get_all_users("admin", limit=50)
        ]
        self.users_table.set_rows(users_rows)

        try:
            owners = self.service.owners.get_all_owners("admin", limit=50)
        except Exception:
            owners = []
        owner_rows = [
            (
                owner["id"],
                owner.get("business_name", ""),
                owner.get("owner_full_name", ""),
                owner.get("verification_status", ""),
                owner.get("rating", 0),
            )
            for owner in owners
        ]
        self.owners_table.set_rows(owner_rows)
