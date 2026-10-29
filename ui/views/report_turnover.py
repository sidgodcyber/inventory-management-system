"""Turnover report table: sortable rows with stockout and run-out highlighting.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from models.reports import TurnoverRow
from ui.components.data_table import TAG_STOCKOUT, TAG_WARNING, Column, DataTable, Row
from ui.theme import Theme
from utils.formatters import format_days, format_number, format_ratio

COLUMNS = (
    Column("sku", "SKU", 100), Column("name", "Product", 190),
    Column("category_name", "Category", 115), Column("quantity_on_hand", "On hand", 70, "e"),
    Column("units_sold", "Issued", 70, "e"), Column("cogs", "COGS", 100, "e"),
    Column("average_inventory_value", "Avg inventory", 110, "e"),
    Column("turnover", "Turnover", 80, "e"), Column("avg_daily_usage", "Usage/day", 80, "e"),
    Column("days_of_stock", "Days of stock", 100, "e"),
)


class TurnoverPanel(ctk.CTkFrame):
    """Export button and a table sorted in memory (the whole report is loaded).

    Args:
        master: Tab frame.
        theme: Shared theme.
        money: Formats an amount with the configured currency.
        warn_days: Days-of-stock threshold for amber highlighting (from config).
        on_export: Called when the export button is pressed.
    """

    def __init__(self, master: Any, theme: Theme, money: Callable[[float], str], warn_days: int,
                 on_export: Callable[[], None]) -> None:
        super().__init__(master, fg_color="transparent")
        self._money = money
        self._warn_days = warn_days
        self._rows: list[TurnoverRow] = []
        self._sort = ("turnover", True)
        ctk.CTkButton(self, text="Export turnover CSV", width=160, command=on_export,
                      **theme.button_style("secondary")).pack(anchor="e", pady=(0, 6))
        self.table = DataTable(self, theme, COLUMNS, on_sort=self._sorted, height=10)
        self.table.pack(fill="both", expand=True)
        self.table.mark_sorted(*self._sort)

    def show(self, rows: list[TurnoverRow]) -> None:
        """Display report rows in the current sort order.

        Args:
            rows: Turnover rows from the report service.
        """
        self._rows = rows
        key, descending = self._sort
        present = sorted((r for r in rows if getattr(r, key) is not None),
                         key=lambda r: getattr(r, key), reverse=descending)
        missing = [r for r in rows if getattr(r, key) is None]  # "no usage" always last
        self.table.set_rows(self._row(r) for r in [*present, *missing])

    def _sorted(self, key: str, descending: bool) -> None:
        """Header clicked: re-sort the loaded rows."""
        self._sort = (key, descending)
        self.show(self._rows)

    def _row(self, row: TurnoverRow) -> Row:
        """Table row; stockouts red, products about to run out amber."""
        urgent = row.days_of_stock is not None and row.days_of_stock <= self._warn_days
        tags = (TAG_STOCKOUT,) if row.quantity_on_hand == 0 else (
            (TAG_WARNING,) if urgent else ())
        values = (row.sku, row.name, row.category_name, row.quantity_on_hand, row.units_sold,
                  self._money(row.cogs), self._money(row.average_inventory_value),
                  format_ratio(row.turnover), format_number(row.avg_daily_usage, 2),
                  format_days(row.days_of_stock))
        return str(row.product_id), values, tags
