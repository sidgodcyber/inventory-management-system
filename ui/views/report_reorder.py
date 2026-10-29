"""Reorder list tab: products at or below their reorder level.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from models.product import Product
from ui.components.data_table import TAG_LOW, TAG_STOCKOUT, Column, DataTable, Row
from ui.theme import Theme

COLUMNS = (
    Column("sku", "SKU", 110, sortable=False), Column("name", "Product", 230, sortable=False),
    Column("category_name", "Category", 130, sortable=False),
    Column("supplier_name", "Supplier", 180, sortable=False),
    Column("quantity_on_hand", "On hand", 80, "e", sortable=False),
    Column("reorder_level", "Reorder level", 100, "e", sortable=False),
    Column("status", "Status", 90, "center", sortable=False),
)


class ReorderPanel(ctk.CTkFrame):
    """Export button and the reorder table.

    Args:
        master: Tab frame.
        theme: Shared theme.
        on_export: Called when the export button is pressed.
    """

    def __init__(self, master: Any, theme: Theme, on_export: Callable[[], None]) -> None:
        super().__init__(master, fg_color="transparent")
        ctk.CTkButton(self, text="Export reorder list CSV", width=180, command=on_export,
                      **theme.button_style("secondary")).pack(anchor="e", pady=(0, 6))
        self.table = DataTable(self, theme, COLUMNS, height=10)
        self.table.pack(fill="both", expand=True)

    def show(self, products: list[Product]) -> None:
        """Display products needing reorder (stockouts darker).

        Args:
            products: Products from the report service, most urgent first.
        """
        self.table.set_rows(_row(p) for p in products)


def _row(product: Product) -> Row:
    """Reorder table row."""
    tag = TAG_STOCKOUT if product.is_out_of_stock else TAG_LOW
    values = (product.sku, product.name, product.category_name, product.supplier_name or "—",
              product.quantity_on_hand, product.reorder_level, product.status)
    return str(product.id), values, (tag,)
