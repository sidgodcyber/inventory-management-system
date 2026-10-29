"""Product picker: a combo box that accepts a list choice or a typed SKU.

Shows live stock on hand, reorder level and unit cost for the chosen product,
with a low-stock warning, so the operator sees the effect before recording a
movement.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from models.product import Product
from ui.theme import Theme

LABEL_SEPARATOR = " — "
_PICK_HINT = "Choose a product (type its SKU or pick from the list)"


def product_label(product: Product) -> str:
    """Picker label for a product.

    Args:
        product: Product to label.

    Returns:
        ``"SKU — Name"``.
    """
    return f"{product.sku}{LABEL_SEPARATOR}{product.name}"


class ProductPicker(ctk.CTkFrame):
    """Combo box plus an information line.

    Args:
        master: Parent widget.
        theme: Shared theme.
        money: Formats an amount with the configured currency.
    """

    def __init__(self, master: Any, theme: Theme, money: Callable[[float], str]) -> None:
        super().__init__(master, fg_color="transparent")
        self._money = money
        self._products: dict[str, Product] = {}
        self.box = ctk.CTkComboBox(self, values=[""], width=380, font=theme.font(),
                                   command=lambda _v: self.show_info())
        self.box.pack(side="left")
        self.box.bind("<KeyRelease>", lambda _e: self.show_info())
        self.info = ctk.CTkLabel(self, text="", font=theme.font(-1),
                                 text_color=theme.color("muted"), anchor="w")
        self.info.pack(side="right", fill="x", expand=True, padx=(12, 0))

    def set_products(self, products: list[Product], keep_id: int | None = None) -> None:
        """Replace the choices, keeping or restoring a selection.

        Args:
            products: Products to offer.
            keep_id: Product to keep selected (e.g. after recording a movement).
        """
        self._products = {product_label(p): p for p in products}
        self.box.configure(values=list(self._products))
        kept = next((label for label, p in self._products.items() if p.id == keep_id), None)
        if kept:
            self.box.set(kept)
        elif self.selected() is None:
            self.box.set("")
        self.show_info()

    def selected(self) -> Product | None:
        """Product matching the box text.

        Returns:
            The product for the full label or a typed SKU (any case), or ``None``.
        """
        text = self.box.get().strip()
        sku = text.split(LABEL_SEPARATOR)[0].upper()
        return self._products.get(text) or next(
            (p for p in self._products.values() if p.sku == sku), None)

    def show_info(self) -> None:
        """Display stock on hand, reorder level and cost for the chosen product."""
        product = self.selected()
        if product is None:
            self.info.configure(text=_PICK_HINT)
            return
        warning = "  ⚠ low stock" if product.is_low_stock else ""
        self.info.configure(
            text=f"On hand: {product.quantity_on_hand} {product.unit}   ·   Reorder: "
                 f"{product.reorder_level}   ·   Cost: {self._money(product.unit_cost)}{warning}")
