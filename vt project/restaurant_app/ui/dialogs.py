"""
restaurant_app/ui/dialogs.py
Small reusable modal dialogs for data entry.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from restaurant_app.ui.styles import COLORS, apply_theme


class FormDialog(tk.Toplevel):
    """Simple modal form dialog that returns a dict of entered values."""

    def __init__(self, parent, title: str, fields: list[dict], width: int = 520):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result: dict | None = None
        self._fields = fields
        self._widgets: dict[str, object] = {}

        apply_theme(self)
        self.configure(padx=16, pady=16)

        body = ttk.Frame(self, style="App.TFrame")
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)

        ttk.Label(body, text=title, style="Section.TLabel").pack(anchor="w")

        form = ttk.Frame(body, style="Card.TFrame", padding=16)
        form.pack(fill="both", expand=True, pady=(12, 0))
        form.columnconfigure(0, weight=1)

        for field in fields:
            self._add_field(form, field)

        button_row = ttk.Frame(body, style="App.TFrame")
        button_row.pack(fill="x", pady=(12, 0))
        ttk.Button(button_row, text="Cancel", style="Ghost.TButton", command=self._cancel).pack(
            side="right"
        )
        ttk.Button(button_row, text="Save", style="Accent.TButton", command=self._submit).pack(
            side="right", padx=(0, 10)
        )

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.transient(parent)
        self.grab_set()
        self._center(parent, width)
        self.wait_window(self)

    def _center(self, parent, width: int) -> None:
        self.update_idletasks()
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
        except Exception:
            px = py = 100
            pw = ph = width
        height = self.winfo_reqheight()
        x = px + max((pw - width) // 2, 0)
        y = py + max((ph - height) // 2, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _add_field(self, parent: ttk.Frame, field: dict) -> None:
        name = field["name"]
        label = field.get("label", name.title())
        kind = field.get("kind", "entry")
        default = field.get("default", "")
        required = field.get("required", False)

        ttk.Label(parent, text=label, style="Field.TLabel").pack(anchor="w", pady=(0, 4))

        if kind == "textarea":
            widget = tk.Text(
                parent,
                height=4,
                wrap="word",
                font=("Segoe UI", 10),
                bg=COLORS.panel,
                fg=COLORS.text,
                insertbackground=COLORS.text,
                relief="solid",
                borderwidth=1,
                highlightthickness=0
            )
            widget.insert("1.0", default)
            widget.pack(fill="x", pady=(0, 12))
        elif kind == "combo":
            widget = ttk.Combobox(
                parent,
                values=field.get("choices", []),
                state="readonly",
            )
            if default:
                widget.set(default)
            elif field.get("choices"):
                widget.set(field["choices"][0])
            widget.pack(fill="x", pady=(0, 12))
        else:
            widget = ttk.Entry(parent)
            if default:
                widget.insert(0, default)
            widget.pack(fill="x", pady=(0, 12))

        widget.required = required  # type: ignore[attr-defined]
        widget.field_name = name  # type: ignore[attr-defined]
        self._widgets[name] = widget

    def _submit(self) -> None:
        data: dict[str, object] = {}
        for name, widget in self._widgets.items():
            if isinstance(widget, tk.Text):
                value = widget.get("1.0", "end").strip()
            else:
                value = widget.get().strip()
            if getattr(widget, "required", False) and not value:
                return
            data[name] = value
        self.result = data
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()
