"""
restaurant_app/ui/customer_tab.py
Customer workspace for restaurant browsing, cart building, and checkout.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from restaurant_app.ui.common_widgets import SearchableTable, SectionHeader
from restaurant_app.ui.dialogs import FormDialog


PAYMENT_METHODS = (
    "credit_card",
    "debit_card",
    "wallet",
    "cash_on_delivery",
)


class CustomerTab(ttk.Frame):
    def __init__(self, parent, service, current_user):
        super().__init__(parent, padding=16)
        self.service = service
        self.current_user = current_user
        self.current_owner_id: int | None = None
        self.cart: list[dict] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        header = SectionHeader(
            self,
            "Customer Dashboard",
            "Browse restaurants, add dishes to your cart, and place orders like a real food app.",
            action_text="Refresh",
            action_command=self.refresh,
        )
        header.pack(fill="x")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, pady=(16, 0))

        browse_tab = ttk.Frame(self.notebook, style="App.TFrame")
        self.menu_tab = ttk.Frame(self.notebook, style="App.TFrame")
        cart_tab = ttk.Frame(self.notebook, style="App.TFrame")
        orders_tab = ttk.Frame(self.notebook, style="App.TFrame")

        self.notebook.add(browse_tab, text="Browse Restaurants")
        self.notebook.add(self.menu_tab, text="Restaurant Menu")
        self.notebook.add(cart_tab, text="My Cart")
        self.notebook.add(orders_tab, text="Order History")

        restaurant_actions = ttk.Frame(browse_tab)
        restaurant_actions.pack(side="bottom", fill="x", pady=(10, 12))
        ttk.Button(restaurant_actions, text="Load Menu", style="Accent.TButton", command=self._load_selected_menu).pack(
            side="left"
        )
        ttk.Button(restaurant_actions, text="Refresh", style="Ghost.TButton", command=self.refresh).pack(side="right")

        self.restaurants_table = SearchableTable(
            browse_tab,
            title="Available Restaurants",
            columns=["Owner ID", "Business", "Owner", "Status", "Rating"],
            subtitle="Select a restaurant, then load its menu.",
            search_hint="Search restaurants",
        )
        self.restaurants_table.pack(fill="both", expand=True)

        dish_actions = ttk.Frame(self.menu_tab)
        dish_actions.pack(side="bottom", fill="x", pady=(0, 12))
        ttk.Button(dish_actions, text="Add to Cart", style="Accent.TButton", command=self._add_selected_dish_to_cart).pack(
            side="left"
        )
        ttk.Button(dish_actions, text="Clear Menu", style="Ghost.TButton", command=self._clear_menu).pack(
            side="left", padx=(10, 0)
        )

        self.dishes_table = SearchableTable(
            self.menu_tab,
            title="Restaurant Menu",
            columns=["Dish ID", "Restaurant", "Name", "Category", "Price"],
            subtitle="Add dishes from the selected restaurant to your cart.",
            search_hint="Search menu",
        )
        self.dishes_table.pack(fill="both", expand=True, pady=(0, 12))

        cart_actions = ttk.Frame(cart_tab)
        cart_actions.pack(side="bottom", fill="x", pady=(10, 0))
        ttk.Button(cart_actions, text="Remove Item", style="Ghost.TButton", command=self._remove_selected_cart_item).pack(
            side="left"
        )
        ttk.Button(cart_actions, text="Clear Cart", style="Danger.TButton", command=self._clear_cart).pack(
            side="left", padx=(10, 0)
        )
        ttk.Button(cart_actions, text="Checkout", style="Accent.TButton", command=self._checkout).pack(
            side="right"
        )

        self.cart_table = SearchableTable(
            cart_tab,
            title="Cart",
            columns=["Dish ID", "Name", "Qty", "Unit Price", "Subtotal"],
            subtitle="Review your cart before placing the order.",
            search_hint="Search cart",
        )
        self.cart_table.pack(fill="both", expand=True)

        orders_split = ttk.Panedwindow(orders_tab, orient=tk.HORIZONTAL)
        orders_split.pack(fill="both", expand=True, pady=(12, 0))

        orders_left = ttk.Frame(orders_split, style="App.TFrame")
        orders_right = ttk.Frame(orders_split, style="App.TFrame")
        orders_split.add(orders_left, weight=1)
        orders_split.add(orders_right, weight=1)

        self.orders_table = SearchableTable(
            orders_left,
            title="Order History",
            columns=["Order ID", "Order #", "Restaurant", "Status", "Total"],
            subtitle="Select an order to view its items.",
            search_hint="Search orders",
        )
        self.orders_table.pack(fill="both", expand=True)
        self.orders_table.tree.bind("<<TreeviewSelect>>", self._on_order_selected)

        self.order_items_table = SearchableTable(
            orders_right,
            title="Order Items",
            columns=["Dish Name", "Qty", "Unit Price", "Subtotal"],
            subtitle="Dishes in the selected order.",
            search_hint="Search items",
        )
        self.order_items_table.pack(fill="both", expand=True)

    def _selected_restaurant_owner_id(self) -> int | None:
        row = self.restaurants_table.get_selected_row()
        if not row:
            return None
        try:
            return int(row[0])
        except Exception:
            return None

    def _selected_dish(self) -> tuple | None:
        return self.dishes_table.get_selected_row()

    def _selected_cart_item(self) -> tuple | None:
        return self.cart_table.get_selected_row()

    def _load_selected_menu(self) -> None:
        owner_id = self._selected_restaurant_owner_id()
        if owner_id is None:
            messagebox.showinfo("Menu", "Select a restaurant first.")
            return
        self.current_owner_id = owner_id
        self._load_menu(owner_id)
        self.notebook.select(self.menu_tab)

    def _load_menu(self, owner_id: int) -> None:
        try:
            dishes = self.service.get_dishes(owner_id=owner_id)
        except Exception as exc:
            messagebox.showerror("Menu", str(exc))
            return
        rows = [
            (
                dish["id"],
                dish.get("business_name", ""),
                dish["name"],
                dish["category"],
                f"${dish['price']:.2f}",
            )
            for dish in dishes
        ]
        self.dishes_table.set_rows(rows)

    def _clear_menu(self) -> None:
        self.current_owner_id = None
        self.dishes_table.clear()

    def _add_selected_dish_to_cart(self) -> None:
        row = self._selected_dish()
        if not row:
            messagebox.showinfo("Cart", "Select a dish first.")
            return
        dish_id = int(row[0])
        restaurant = str(row[1])
        name = str(row[2])
        price = float(str(row[4]).replace("$", ""))
        if self.current_owner_id is None:
            self.current_owner_id = self._selected_restaurant_owner_id()

        existing = next((item for item in self.cart if item["dish_id"] == dish_id), None)
        if existing:
            existing["quantity"] += 1
        else:
            self.cart.append(
                {
                    "dish_id": dish_id,
                    "owner_id": self.current_owner_id,
                    "restaurant": restaurant,
                    "name": name,
                    "quantity": 1,
                    "unit_price": price,
                }
            )
        self._sync_cart_view()

    def _remove_selected_cart_item(self) -> None:
        row = self._selected_cart_item()
        if not row:
            messagebox.showinfo("Cart", "Select a cart item first.")
            return
        dish_id = int(row[0])
        self.cart = [item for item in self.cart if item["dish_id"] != dish_id]
        self._sync_cart_view()

    def _clear_cart(self) -> None:
        self.cart.clear()
        self._sync_cart_view()

    def _sync_cart_view(self) -> None:
        rows = []
        for item in self.cart:
            subtotal = item["unit_price"] * item["quantity"]
            rows.append(
                (
                    item["dish_id"],
                    item["name"],
                    item["quantity"],
                    f"${item['unit_price']:.2f}",
                    f"${subtotal:.2f}",
                )
            )
        self.cart_table.set_rows(rows)

    def _checkout(self) -> None:
        if not self.cart:
            messagebox.showinfo("Checkout", "Your cart is empty.")
            return

        dialog = FormDialog(
            self,
            "Checkout",
            [
                {"name": "delivery_address", "label": "Delivery Address", "required": True},
                {"name": "payment_method", "label": "Payment Method", "kind": "combo", "choices": PAYMENT_METHODS, "default": PAYMENT_METHODS[0], "required": True},
                {"name": "special_instructions", "label": "Special Instructions", "kind": "textarea"},
            ],
        )
        if not dialog.result:
            return

        cart_items = [
            {"dish_id": item["dish_id"], "quantity": item["quantity"]}
            for item in self.cart
        ]
        try:
            order = self.service.create_order(
                customer_id=self.current_user["id"],
                cart_items=cart_items,
                delivery_address=dialog.result["delivery_address"],
                payment_method=dialog.result["payment_method"],
                special_instructions=dialog.result.get("special_instructions") or None,
            )
            messagebox.showinfo(
                "Order placed",
                f"Order {order['order_number']} placed successfully for ${order['total_amount']:.2f}.",
            )
            self._clear_cart()
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Checkout", str(exc))

    def refresh(self) -> None:
        try:
            owners = self.service.owners.get_all_owners("admin", limit=100)
        except Exception:
            owners = []
        restaurant_rows = [
            (
                owner["id"],
                owner.get("business_name", ""),
                owner.get("owner_full_name", ""),
                owner.get("verification_status", ""),
                owner.get("rating", 0),
            )
            for owner in owners
            if owner.get("verification_status") in ("verified", "pending")
        ]
        self.restaurants_table.set_rows(restaurant_rows)

        if self.current_owner_id is not None:
            self._load_menu(self.current_owner_id)
        else:
            self.dishes_table.clear()

        try:
            orders = self.service.orders.get_customer_orders(
                self.current_user["id"], self.current_user["id"], self.current_user["role"], limit=100
            )
        except Exception:
            orders = []
        order_rows = [
            (
                order["id"],
                order["order_number"],
                order.get("business_name", ""),
                order["status"],
                f"${order['total_amount']:.2f}",
            )
            for order in orders
        ]
        self.orders_table.set_rows(order_rows)
        self.order_items_table.clear()
        self._sync_cart_view()

    def _on_order_selected(self, event=None) -> None:
        row = self.orders_table.get_selected_row()
        if not row:
            self.order_items_table.clear()
            return
        try:
            order_id = int(row[0])
            order = self.service.orders.get_order(order_id, self.current_user["id"], self.current_user["role"])
            item_rows = [
                (
                    item.get("dish_name", ""),
                    item.get("quantity", 0),
                    f"${item.get('unit_price', 0.0):.2f}",
                    f"${item.get('subtotal', 0.0):.2f}"
                )
                for item in order.get("items", [])
            ]
            self.order_items_table.set_rows(item_rows)
        except Exception:
            self.order_items_table.clear()
