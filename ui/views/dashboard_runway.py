"""Stock runway: what is about to run out, most urgent first.

The dashboard's main block. Each at-risk product shows how much of its reorder
level is left as a thin bar in the screen's one hue, with days of stock and the
minimum to order beside it, so the next order can be read straight off the row.
Spare rows list what will reach its reorder level next, in grey.

Layer: ui/views
Author: Siddhi Baluja
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from models.product import Product
from ui.theme import Theme
from utils.formatters import format_days

# Fixed widths so every row shares the header's columns.
_ON_HAND, _BAR, _DAYS, _ORDER = 74, 110, 76, 62


def order_at_least(product: Product) -> int:
    """Smallest order that lifts stock above the reorder level.

    Args:
        product: Product at or below its reorder level.

    Returns:
        Units to order.
    """
    return product.reorder_level - product.quantity_on_hand + 1


def next_to_run_out(products: Sequence[Product], days: dict[int, float | None],
                    count: int) -> list[Product]:
    """Healthy products that will run out soonest.

    Args:
        products: Every active product.
        days: Days of stock left by product id.
        count: How many to return.

    Returns:
        Products above their reorder level, fewest days left first.
    """
    healthy = [p for p in products if not p.is_low_stock and days.get(p.id) is not None]
    return sorted(healthy, key=lambda p: days[p.id])[:max(count, 0)]


def by_urgency(products: Sequence[Product]) -> list[Product]:
    """Sort products by how much of their reorder level is left.

    Args:
        products: Products at or below their reorder level.

    Returns:
        Stockouts first, then the lowest share of the reorder level.
    """
    return sorted(products, key=lambda p: (p.quantity_on_hand / max(p.reorder_level, 1), p.name))


class StockRunway(ctk.CTkFrame):
    """Card listing the products that need reordering.

    Args:
        master: Parent widget.
        theme: Shared theme.
        limit: Rows shown before "View all" takes over (from config).
        on_view_all: Opens the full low-stock list.
    """

    def __init__(self, master: Any, theme: Theme, limit: int,
                 on_view_all: Callable[[], None]) -> None:
        super().__init__(master, **theme.card_style())
        self._theme = theme
        self._limit = limit
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(14, 6))
        self.title = ctk.CTkLabel(header, text="Stock runway", font=theme.font(2, "bold"))
        self.title.pack(side="left")
        self.more = ctk.CTkButton(header, text="View all", width=70, height=26,
                                  command=on_view_all, **theme.button_style("secondary"))
        self.more.pack(side="right")
        self._row(self, ("Product", "On hand", "", "Stock left", "Order"), head=True)
        self.rows = ctk.CTkFrame(self, fg_color="transparent")
        self.rows.pack(fill="both", expand=True, padx=2, pady=(0, 10))

    def _row(self, master: Any, texts: Sequence[str], head: bool = False,
             days_color: str = "muted") -> ctk.CTkFrame:
        """One row of the five fixed columns; returns the empty slot for its bar."""
        row = ctk.CTkFrame(master, fg_color="transparent", height=20 if head else 36)
        row.pack(fill="x", padx=20 if head else 18)
        row.pack_propagate(False)
        font = self._theme.font(-2 if head else 0)
        muted = self._theme.color("muted")
        name, on_hand, _bar, days, order = texts
        for text, width, color in ((order, _ORDER, muted if head else self._theme.color("text")),
                                   (days, _DAYS, muted if head else self._theme.color(days_color))):
            ctk.CTkLabel(row, text=text, width=width, anchor="e", font=font,
                         text_color=color).pack(side="right")
        slot = ctk.CTkFrame(row, fg_color="transparent", width=_BAR, height=8)
        slot.pack(side="right", padx=(10, 6))
        ctk.CTkLabel(row, text=on_hand, width=_ON_HAND, anchor="e", font=font,
                     text_color=muted).pack(side="right")
        ctk.CTkLabel(row, text=name, anchor="w", font=font,
                     text_color=muted if head else self._theme.color("text")).pack(
            side="left", fill="x", expand=True)
        return slot

    def show(self, products: Sequence[Product], watch: Sequence[Product],
             days: dict[int, float | None]) -> None:
        """Display the most urgent products, then what is next.

        Args:
            products: Products at or below their reorder level.
            watch: Every active product, to fill spare rows with the next to run out.
            days: Days of stock left by product id (``None`` when nothing was issued).
        """
        for child in self.rows.winfo_children():
            child.destroy()
        ordered = by_urgency(products)
        self.title.configure(text=f"Stock runway · {len(ordered)} to reorder")
        for product in ordered[:self._limit]:
            self._add_product(product, days.get(product.id))
        spare = next_to_run_out(watch, days, self._limit - len(ordered))
        if spare:
            ctk.CTkLabel(self.rows, text="Next to reach reorder level", height=28, anchor="w",
                         font=self._theme.font(-2), text_color=self._theme.color("muted")).pack(
                fill="x", padx=18, pady=(4, 0))
        for product in spare:
            self._add_healthy(product, days[product.id])

    def _add_product(self, product: Product, days: float | None) -> None:
        """Add one product: figures in ink, the bar in the screen's one hue."""
        out = product.is_out_of_stock
        left = "Out of stock" if out else ("—" if days is None else format_days(days))
        slot = self._row(self.rows, (product.name, f"{product.quantity_on_hand} / "
                                     f"{product.reorder_level}", "", left,
                                     str(order_at_least(product))),
                         days_color="danger" if out else "text")
        self._bar(slot, product, self._theme.pair("hue"))

    def _add_healthy(self, product: Product, days: float) -> None:
        """Add one product that needs no order yet: its bar stays grey."""
        slot = self._row(self.rows, (product.name, f"{product.quantity_on_hand} / "
                                     f"{product.reorder_level}", "", format_days(days), "—"))
        self._bar(slot, product, self._theme.pair("comparison"))

    def _bar(self, slot: Any, product: Product, color: tuple[str, str]) -> None:
        """Share of the reorder level left; a zero draws the bare track, with no stub."""
        share = min(product.quantity_on_hand / max(product.reorder_level, 1), 1.0)
        bar = ctk.CTkProgressBar(slot, width=_BAR, height=6,
                                 progress_color=color if share else self._theme.pair("raised"))
        bar.set(share)
        bar.pack()
