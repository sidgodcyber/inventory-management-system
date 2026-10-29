"""Filter bar for the stock transaction history (product, type, date range).

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from core.constants import TRANSACTION_TYPES
from models.filters import TransactionFilter
from models.product import Product
from ui.theme import Theme
from utils.validators import Validator

ALL_PRODUCTS = "All products"
ALL_TYPES = "All types"


class HistoryFilterBar(ctk.CTkFrame):
    """"History" heading, filter inputs and Apply / Clear / Export buttons.

    Args:
        master: Parent widget.
        theme: Shared theme.
        on_apply: Called when Apply is pressed.
        on_clear: Called after the inputs are reset.
        on_export: Called when Export CSV is pressed.
    """

    def __init__(self, master: Any, theme: Theme, on_apply: Callable[[], None],
                 on_clear: Callable[[], None], on_export: Callable[[], None]) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_clear = on_clear
        ctk.CTkLabel(self, text="History", font=theme.font(2, "bold")).pack(side="left")
        self.product = ctk.CTkOptionMenu(self, values=[ALL_PRODUCTS], width=200,
                                         dynamic_resizing=False)
        self.product.pack(side="left", padx=(14, 0))
        self.kind = ctk.CTkOptionMenu(self, values=[ALL_TYPES, *TRANSACTION_TYPES], width=110)
        self.kind.pack(side="left", padx=(8, 0))
        self.date_from = ctk.CTkEntry(self, width=140)
        self.date_from.pack(side="left", padx=(8, 0))
        self.date_to = ctk.CTkEntry(self, width=140)
        self.date_to.pack(side="left", padx=(6, 0))
        for text, command, kind in (("Export CSV", on_export, "secondary"),
                                    ("Clear", self.clear, "secondary"), ("Apply", on_apply, "primary")):
            ctk.CTkButton(self, text=text, width=90, command=command,
                          **theme.button_style(kind)).pack(side="right", padx=(6, 0))

    def set_products(self, labels: list[str]) -> None:
        """Offer these product labels in the product filter.

        Args:
            labels: Picker labels (``"SKU — Name"``).
        """
        self.product.configure(values=[ALL_PRODUCTS, *labels])

    def set_date_hint(self, example: str) -> None:
        """Show an example date (configured format) in the date boxes.

        Args:
            example: Today's date formatted with the date-format setting.
        """
        self.date_from.configure(placeholder_text=f"From e.g. {example}")
        self.date_to.configure(placeholder_text=f"To e.g. {example}")

    def read(self, products: dict[str, Product], date_format: str) -> TransactionFilter:
        """Build a filter from the inputs.

        Args:
            products: ``{label: product}`` used to resolve the product filter.
            date_format: ``strftime`` pattern for the date boxes.

        Returns:
            The transaction filter.

        Raises:
            ValidationError: If a date does not match the format.
        """
        product = products.get(self.product.get())
        kind = self.kind.get()
        return TransactionFilter(
            product_id=product.id if product else None,
            tx_type=None if kind == ALL_TYPES else kind,
            date_from=Validator.date(self.date_from.get(), "From date", date_format),
            date_to=Validator.date(self.date_to.get(), "To date", date_format),
        )

    def clear(self) -> None:
        """Reset every input and notify the owner."""
        self.product.set(ALL_PRODUCTS)
        self.kind.set(ALL_TYPES)
        for entry in (self.date_from, self.date_to):
            entry.delete(0, "end")
        self._on_clear()
