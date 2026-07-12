"""
restaurant_app/ui/common_widgets.py
Reusable visual building blocks for the Tkinter UI.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class SectionHeader(ttk.Frame):
    """Consistent title/subtitle block for each screen."""

    def __init__(self, parent, title: str, subtitle: str = "", action_text: str = None, action_command=None):
        super().__init__(parent, style="App.TFrame")
        self.columnconfigure(0, weight=1)
        left = ttk.Frame(self, style="App.TFrame")
        left.grid(row=0, column=0, sticky="w")
        ttk.Label(left, text=title, style="Section.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(left, text=subtitle, style="Muted.TLabel", wraplength=900).pack(anchor="w", pady=(4, 0))
        if action_text and action_command:
            ttk.Button(self, text=action_text, style="Ghost.TButton", command=action_command).grid(
                row=0, column=1, sticky="e", padx=(12, 0)
            )


class MetricCard(tk.Frame):
    """Small dashboard statistic card."""

    def __init__(self, parent, label: str, value_var: tk.StringVar, hint: str = "", card_type: str = "default", bg_color: str = "", border_color: str = ""):
        super().__init__(parent, highlightthickness=1)
        self.card_type = card_type or label
        self.label_text = label
        self.hint_text = hint
        self.value_var = value_var
        self.pack_propagate(False) # optional
        
        self.inner = tk.Frame(self, padx=14, pady=14)
        self.inner.pack(fill="both", expand=True)
        
        self.lbl_title = tk.Label(self.inner, text=label, font=("Segoe UI", 9))
        self.lbl_title.pack(anchor="w")
        
        self.lbl_val = tk.Label(self.inner, textvariable=value_var, font=("Segoe UI Semibold", 20))
        self.lbl_val.pack(anchor="w", pady=(8, 0))
        
        self.lbl_hint = None
        if hint:
            self.lbl_hint = tk.Label(self.inner, text=hint, font=("Segoe UI", 9))
            self.lbl_hint.pack(anchor="w", pady=(6, 0))
            
        self.refresh_colors()

    def refresh_colors(self) -> None:
        from restaurant_app.ui.styles import COLORS
        is_dark = COLORS.is_dark
        
        if self.card_type == "Users":
            bg, border = ("#1e293b", "#3b82f6") if is_dark else ("#eff6ff", "#bfdbfe")
            fg_title, fg_val, fg_hint = ("#93c5fd", "#f8fafc", "#93c5fd") if is_dark else ("#1e40af", "#1e3a8a", "#60a5fa")
        elif self.card_type == "Owners":
            bg, border = ("#062f4f", "#10b981") if is_dark else ("#f0fdf4", "#bbf7d0")
            fg_title, fg_val, fg_hint = ("#6ee7b7", "#f8fafc", "#6ee7b7") if is_dark else ("#166534", "#14532d", "#4ade80")
        elif self.card_type == "Dishes":
            bg, border = ("#3c2f1f", "#f59e0b") if is_dark else ("#fefce8", "#fef08a")
            fg_title, fg_val, fg_hint = ("#fde047", "#f8fafc", "#fde047") if is_dark else ("#854d0e", "#713f12", "#eab308")
        elif self.card_type == "Orders":
            bg, border = ("#451a03", "#f97316") if is_dark else ("#fff7ed", "#fed7aa")
            fg_title, fg_val, fg_hint = ("#fdba74", "#f8fafc", "#fdba74") if is_dark else ("#9a3412", "#7c2d12", "#fb923c")
        else:
            bg = COLORS.panel
            border = COLORS.border
            fg_title = COLORS.muted
            fg_val = COLORS.heading
            fg_hint = COLORS.muted
            
        self.configure(bg=bg, highlightbackground=border, highlightcolor=border)
        self.inner.configure(bg=bg)
        self.lbl_title.configure(bg=bg, fg=fg_title)
        self.lbl_val.configure(bg=bg, fg=fg_val)
        if self.lbl_hint:
            self.lbl_hint.configure(bg=bg, fg=fg_hint)


class SearchableTable(ttk.Frame):
    """A card-like table with a built-in search box and scrollbars."""

    def __init__(self, parent, title: str, columns: list[str], subtitle: str = "", search_hint: str = "Filter rows"):
        super().__init__(parent, style="Card.TFrame", padding=12)
        self.columns = list(columns)
        self._rows: list[tuple] = []
        self._filtered_rows: list[tuple] = []
        self._columns_joiner = " | "

        top = ttk.Frame(self, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text=title, style="CardTitle.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(top, text=subtitle, style="CardText.TLabel", wraplength=900).pack(anchor="w", pady=(3, 0))

        tool_row = ttk.Frame(self, style="Card.TFrame")
        tool_row.pack(fill="x", pady=(10, 10))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._apply_filter)
        ttk.Label(tool_row, text=search_hint, style="CardText.TLabel").pack(side="left")
        self.search_entry = ttk.Entry(tool_row, textvariable=self.search_var, width=30)
        self.search_entry.pack(side="right", padx=(10, 0))

        table_frame = ttk.Frame(self, style="Card.TFrame")
        table_frame.pack(fill="both", expand=True)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_frame, columns=self.columns, show="headings", height=8)
        for column in self.columns:
            self.tree.heading(column, text=column)
            self.tree.column(column, width=140, anchor="w")

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        self.empty_var = tk.StringVar(value="No records to display.")
        self.empty_label = ttk.Label(self, textvariable=self.empty_var, style="CardText.TLabel")

    def set_rows(self, rows: list[tuple]) -> None:
        self._rows = list(rows)
        self._apply_filter()

    def get_selected_row(self) -> tuple | None:
        """Return the currently selected row values, if any."""
        selection = self.tree.selection()
        if not selection:
            return None
        return tuple(self.tree.item(selection[0], "values"))

    def get_selected_rows(self) -> list[tuple]:
        """Return all selected row values."""
        rows = []
        for item in self.tree.selection():
            rows.append(tuple(self.tree.item(item, "values")))
        return rows

    def clear(self) -> None:
        self._rows = []
        self._filtered_rows = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.empty_var.set("No records to display.")
        self.empty_label.pack_forget()

    def _apply_filter(self, *_args) -> None:
        query = self.search_var.get().strip().lower()
        if query:
            self._filtered_rows = [
                row for row in self._rows
                if query in " ".join("" if value is None else str(value) for value in row).lower()
            ]
        else:
            self._filtered_rows = list(self._rows)

        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self._filtered_rows:
            self.empty_var.set("No matching records found.")
            self.empty_label.pack(anchor="w", pady=(8, 0))
            return

        self.empty_label.pack_forget()
        for row in self._filtered_rows:
            self.tree.insert("", "end", values=row)


class Pill:
    """Compact capsule label for session and status information."""

    def __init__(self, parent, textvariable=None, text: str = "", color: str = ""):
        self.color = color
        self._label = tk.Label(
            parent,
            text=text,
            textvariable=textvariable,
            font=("Segoe UI Semibold", 9),
            padx=10,
            pady=4,
        )
        self.refresh_colors()

    def refresh_colors(self) -> None:
        from restaurant_app.ui.styles import COLORS
        bg = self.color or COLORS.accent
        self._label.configure(bg=bg, fg="#ffffff")

    def pack(self, *args, **kwargs):
        return self._label.pack(*args, **kwargs)

    def grid(self, *args, **kwargs):
        return self._label.grid(*args, **kwargs)

    def place(self, *args, **kwargs):
        return self._label.place(*args, **kwargs)

    def configure(self, *args, **kwargs):
        return self._label.configure(*args, **kwargs)

    config = configure
