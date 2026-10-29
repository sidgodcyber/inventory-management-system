"""Row of five KPI cards for the dashboard.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from models.reports import DashboardStats
from ui.components.stat_card import StatCard
from ui.theme import Theme
from utils.formatters import format_ratio

# (key, title, accent palette colour) in display order.
_CARDS: tuple[tuple[str, str, str], ...] = (
    ("products", "Active products", "accent"),
    ("value", "Stock value (at cost)", "accent"),
    ("low", "Low stock", "warning"),
    ("stockouts", "Stockouts", "danger"),
    ("turnover", "Inventory turnover", "success"),
)


class KpiCards(ctk.CTkFrame):
    """Equal-width stat cards for the headline numbers.

    Args:
        master: Parent widget.
        theme: Shared theme.
    """

    def __init__(self, master: Any, theme: Theme) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(tuple(range(len(_CARDS))), weight=1, uniform="cards")
        self.cards: dict[str, StatCard] = {}
        for column, (key, title, accent) in enumerate(_CARDS):
            card = StatCard(self, theme, title, accent)
            card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0))
            self.cards[key] = card

    def show(self, stats: DashboardStats, money: Callable[[float], str]) -> None:
        """Fill the cards; low-stock and stockout accents turn green at zero.

        Args:
            stats: Figures from the report service.
            money: Formats the stock value with the configured currency.
        """
        cards = self.cards
        cards["products"].set(str(stats.total_products), "SKUs currently stocked")
        cards["value"].set(money(stats.total_stock_value), "quantity × unit cost")
        cards["low"].set(str(stats.low_stock_count), "at or below reorder level",
                         "warning" if stats.low_stock_count else "success")
        cards["stockouts"].set(str(stats.stockout_count), "products with zero stock",
                               "danger" if stats.stockout_count else "success")
        cards["turnover"].set(format_ratio(stats.turnover),
                              f"COGS ÷ avg inventory · {stats.period_days} days")
