"""
restaurant_app/ui/owner_tab.py
Owner workspace for dishes and restaurant analytics.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from restaurant_app.ui.common_widgets import MetricCard, SearchableTable, SectionHeader
from restaurant_app.ui.dialogs import FormDialog
from restaurant_app.ui.styles import COLORS


class OwnerTab(ttk.Frame):
    def __init__(self, parent, service, current_user):
        super().__init__(parent, padding=16)
        self.service = service
        self.current_user = current_user
        self.total_dishes_var = tk.StringVar(value="0")
        self.active_dishes_var = tk.StringVar(value="0")
        self.revenue_var = tk.StringVar(value="$0.00")
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        header = SectionHeader(
            self,
            "Restaurant Owner",
            "Manage your restaurant profile, dishes, and analytics in one workspace.",
            action_text="Refresh",
            action_command=self.refresh,
        )
        header.pack(fill="x")

        profile = ttk.Frame(self, style="Card.TFrame", padding=14)
        profile.pack(fill="x", pady=(16, 12))
        self.profile_var = tk.StringVar(value="No owner profile found.")
        ttk.Label(profile, text="Profile", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(profile, textvariable=self.profile_var, style="Muted.TLabel").pack(anchor="w", pady=(8, 0))

        cards = ttk.Frame(self)
        cards.pack(fill="x", pady=(0, 12))
        for idx, (label, var, hint) in enumerate(
            [
                ("Total Dishes", self.total_dishes_var, "Menu count"),
                ("Active Dishes", self.active_dishes_var, "Available now"),
                ("Revenue", self.revenue_var, "This month"),
            ]
        ):
            card = MetricCard(cards, label, var, hint=hint)
            card.grid(row=0, column=idx, sticky="nsew", padx=(0 if idx == 0 else 12, 0))
            cards.columnconfigure(idx, weight=1)

        split = ttk.Notebook(self)
        split.pack(fill="both", expand=True)

        dishes_frame = ttk.Frame(split, style="App.TFrame")
        orders_frame = ttk.Frame(split, style="App.TFrame")
        split.add(dishes_frame, text="Dishes")
        split.add(orders_frame, text="Incoming Orders")

        dish_actions = ttk.Frame(dishes_frame)
        dish_actions.pack(side="bottom", fill="x", pady=(10, 0))
        ttk.Button(dish_actions, text="Add Dish", style="Accent.TButton", command=self._add_dish).pack(side="left")
        ttk.Button(dish_actions, text="Edit Dish", style="Ghost.TButton", command=self._edit_dish).pack(side="left", padx=(10, 0))
        ttk.Button(dish_actions, text="Toggle Status", style="Ghost.TButton", command=self._toggle_dish).pack(side="left", padx=(10, 0))
        ttk.Button(dish_actions, text="Delete Dish", style="Danger.TButton", command=self._delete_dish).pack(side="left", padx=(10, 0))

        self.dishes_table = SearchableTable(
            dishes_frame,
            title="Dishes",
            columns=["ID", "Name", "Category", "Price", "Status"],
            subtitle="Search by name, category, price, or availability.",
            search_hint="Search dishes",
        )
        self.dishes_table.pack(fill="both", expand=True)

        order_actions = ttk.Frame(orders_frame)
        order_actions.pack(side="bottom", fill="x", pady=(10, 0))
        ttk.Button(order_actions, text="Advance Order", style="Accent.TButton", command=self._advance_order).pack(side="left")
        ttk.Button(order_actions, text="Refresh", style="Ghost.TButton", command=self.refresh).pack(side="right")

        self.orders_table = SearchableTable(
            orders_frame,
            title="Incoming Orders",
            columns=["Order ID", "Order #", "Customer", "Status", "Total"],
            subtitle="Track incoming customer orders for your restaurant.",
            search_hint="Search orders",
        )
        self.orders_table.pack(fill="both", expand=True, pady=(12, 0))
        self.orders_table.tree.bind("<Button-3>", self._show_order_context_menu)

    def _selected_dish_id(self) -> int | None:
        row = self.dishes_table.get_selected_row()
        if not row:
            return None
        try:
            return int(row[0])
        except Exception:
            return None

    def _selected_order(self) -> tuple[int | None, str | None]:
        row = self.orders_table.get_selected_row()
        if not row:
            return None, None
        try:
            return int(row[0]), str(row[3])
        except Exception:
            return None, None

    def _add_dish(self) -> None:
        categories = self.service.dishes.get_categories()
        dialog = FormDialog(
            self,
            "Add Dish",
            [
                {"name": "name", "label": "Dish Name", "required": True},
                {"name": "category", "label": "Category", "kind": "combo", "choices": categories, "required": True},
                {"name": "price", "label": "Price", "required": True},
                {"name": "description", "label": "Description", "kind": "textarea"},
                {"name": "max_discount", "label": "Max Discount %", "default": "30"},
            ],
        )
        if not dialog.result:
            return
        try:
            self.service.create_dish(
                self.current_user["id"],
                self.current_user["role"],
                name=dialog.result["name"],
                category=dialog.result["category"],
                price=float(dialog.result["price"]),
                description=dialog.result.get("description") or None,
                max_discount=float(dialog.result.get("max_discount") or 30),
            )
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Add Dish", str(exc))

    def _edit_dish(self) -> None:
        dish_id = self._selected_dish_id()
        if dish_id is None:
            messagebox.showinfo("Edit Dish", "Select a dish first.")
            return
        try:
            dish = self.service.dishes.get_dish(dish_id)
        except Exception as exc:
            messagebox.showerror("Edit Dish", str(exc))
            return
        dialog = FormDialog(
            self,
            "Edit Dish",
            [
                {"name": "name", "label": "Dish Name", "default": dish["name"], "required": True},
                {"name": "category", "label": "Category", "kind": "combo", "choices": self.service.dishes.get_categories(), "default": dish["category"], "required": True},
                {"name": "price", "label": "Price", "default": str(dish["price"]), "required": True},
                {"name": "description", "label": "Description", "kind": "textarea", "default": dish.get("description") or ""},
                {"name": "max_discount_allowed", "label": "Max Discount %", "default": str(dish.get("max_discount_allowed", 30))},
            ],
        )
        if not dialog.result:
            return
        try:
            self.service.update_dish(
                self.current_user["id"],
                self.current_user["role"],
                dish_id,
                {
                    "name": dialog.result["name"],
                    "category": dialog.result["category"],
                    "price": float(dialog.result["price"]),
                    "description": dialog.result.get("description") or None,
                    "max_discount_allowed": float(dialog.result.get("max_discount_allowed") or 30),
                },
            )
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Edit Dish", str(exc))

    def _toggle_dish(self) -> None:
        dish_id = self._selected_dish_id()
        if dish_id is None:
            messagebox.showinfo("Toggle Dish", "Select a dish first.")
            return
        try:
            self.service.toggle_dish_status(self.current_user["id"], self.current_user["role"], dish_id)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Toggle Dish", str(exc))

    def _delete_dish(self) -> None:
        dish_id = self._selected_dish_id()
        if dish_id is None:
            messagebox.showinfo("Delete Dish", "Select a dish first.")
            return
        if not messagebox.askyesno("Delete Dish", "Delete the selected dish?"):
            return
        try:
            self.service.delete_dish(self.current_user["id"], self.current_user["role"], dish_id)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Delete Dish", str(exc))

    def _advance_order(self) -> None:
        order_id, status = self._selected_order()
        if order_id is None:
            messagebox.showinfo("Order", "Select an order first.")
            return
        next_status = {
            "pending": "confirmed",
            "confirmed": "preparing",
            "preparing": "on_the_way",
            "on_the_way": "delivered",
        }.get(status or "")
        if not next_status:
            messagebox.showinfo("Order", f"No next step available for status '{status}'.")
            return
        try:
            self.service.update_order_status(order_id, next_status, self.current_user["id"], self.current_user["role"])
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Order", str(exc))

    def refresh(self) -> None:
        try:
            owner = self.service.owners.get_owner_by_user(self.current_user["id"])
            self.profile_var.set(
                f"{owner['business_name']} | License: {owner['license_number']} | Status: {owner['verification_status']}"
            )
            dishes = self.service.dishes.get_owner_dishes(self.current_user["id"], "owner", limit=100)
            self.total_dishes_var.set(str(len(dishes)))
            self.active_dishes_var.set(str(sum(1 for d in dishes if d["status"] == "active")))
            total_revenue = 0.0
            try:
                analytics = self.service.owners.get_analytics("owner", self.current_user["id"], owner["id"])
                total_revenue = analytics.get("total_revenue", 0.0)
            except Exception:
                pass
            self.revenue_var.set(f"${total_revenue:.2f}")

            rows = [
                (dish["id"], dish["name"], dish["category"], f"${dish['price']:.2f}", dish["status"])
                for dish in dishes
            ]
            self.dishes_table.set_rows(rows)

            orders = self.service.get_owner_orders(self.current_user["id"], self.current_user["role"], limit=100)
            order_rows = [
                (
                    order["id"],
                    order["order_number"],
                    order.get("customer_name", ""),
                    order["status"],
                    f"${order['total_amount']:.2f}",
                )
                for order in orders
            ]
            self.orders_table.set_rows(order_rows)
        except Exception as exc:
            self.profile_var.set(str(exc))
            self.total_dishes_var.set("0")
            self.active_dishes_var.set("0")
            self.revenue_var.set("$0.00")
            self.dishes_table.clear()
            self.orders_table.clear()

    def _show_order_context_menu(self, event) -> None:
        item = self.orders_table.tree.identify_row(event.y)
        if not item:
            return
        self.orders_table.tree.selection_set(item)
        
        row = self.orders_table.get_selected_row()
        if not row:
            return
        order_id = int(row[0])
        current_status = row[3]
        
        menu = tk.Menu(
            self,
            tearoff=0,
            bg=COLORS.panel,
            fg=COLORS.text,
            activebackground=COLORS.accent,
            activeforeground="#ffffff",
            relief="solid",
            borderwidth=1
        )
        statuses = ["pending", "confirmed", "preparing", "on_the_way", "delivered", "cancelled"]
        for s in statuses:
            label = s.replace("_", " ").title()
            if s == current_status:
                label += " ✓"
            menu.add_command(label=label, command=lambda status=s, oid=order_id: self._update_order_status(oid, status))
        menu.post(event.x_root, event.y_root)

    def _update_order_status(self, order_id: int, new_status: str) -> None:
        try:
            self.service.update_order_status(order_id, new_status, self.current_user["id"], self.current_user["role"])
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Order Status", str(exc))
