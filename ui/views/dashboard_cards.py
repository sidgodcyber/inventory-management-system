"""Headline figures for the dashboard, in one container split by dividers.

Layer: ui/views
Author: Siddhi Baluja
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from models.reports import DashboardStats
from ui.components.stat_card import StatCard
from ui.theme import Theme
from utils.formatters import format_ratio

# (key, label, is the screen's answer figure) in display order.
_CELLS: tuple[tuple[str, str, bool], ...] = (
    ("reorder", "Needs reordering", True),
    ("stockouts", "Out of stock", False),
    ("value", "Stock value at cost", False),
    ("turnover", "Inventory turnover", False),
    ("products", "Products stocked", False),
)


class KpiCards(ctk.CTkFrame):
    """A card split into equal columns, the screen's answer first.

    Args:
        master: Parent widget.
        theme: Shared theme.
    """

    def __init__(self, master: Any, theme: Theme) -> None:
        super().__init__(master, **theme.card_style())
        self.cards: dict[str, StatCard] = {}
        for index, (key, label, lead) in enumerate(_CELLS):
            if index:
                ctk.CTkFrame(self, width=1, height=10, corner_radius=0,
                             fg_color=theme.pair("border")).grid(row=0, column=index * 2 - 1,
                                                                 sticky="ns", pady=14)
            self.grid_columnconfigure(index * 2, weight=1, uniform="kpi")
            cell = StatCard(self, theme, label, lead)
            cell.grid(row=0, column=index * 2, sticky="ew", padx=20, pady=12)
            self.cards[key] = cell

    def show(self, stats: DashboardStats, money: Callable[[float], str]) -> None:
        """Fill the cells; red is kept for real stockouts, and a zero is grey.

        Args:
            stats: Figures from the report service.
            money: Formats the stock value with the configured currency.
        """
        cards = self.cards
        cards["reorder"].set(str(stats.low_stock_count), "at or below reorder level",
                             "text" if stats.low_stock_count else "muted")
        cards["stockouts"].set(str(stats.stockout_count), "products at zero",
                               "danger" if stats.stockout_count else "muted")
        cards["value"].set(money(stats.total_stock_value), "quantity × unit cost")
        cards["turnover"].set(format_ratio(stats.turnover),
                              f"COGS ÷ avg inventory, {stats.period_days} days")
        cards["products"].set(str(stats.total_products), "active SKUs")
