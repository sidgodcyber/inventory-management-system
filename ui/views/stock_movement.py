"""Stock movement panel: pick a product and record stock in, stock out or adjust.

The panel only collects input and calls :class:`services.stock_service.StockService`;
every rule (no negative stock, adjust needs a reason) is enforced there.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from core.constants import TX_ADJUST, TX_IN, TX_OUT
from models.movement import MovementResult
from models.product import Product
from ui.components.product_picker import ProductPicker

if TYPE_CHECKING:
    from ui.views.base_view import BaseView

#: Movement selector labels mapped to transaction types (and back).
MOVEMENTS = {"Stock In": TX_IN, "Stock Out": TX_OUT, "Adjust": TX_ADJUST}
MOVEMENT_LABELS = {kind: label for label, kind in MOVEMENTS.items()}


class MovementPanel(ctk.CTkFrame):
    """Card with product picker, movement type, quantity, cost, note and submit.

    Args:
        master: Parent widget.
        view: Owning screen (services, theme, safe calls, toasts, money format).
        on_recorded: Called with the result after a successful movement.
    """

    def __init__(self, master: Any, view: BaseView,
                 on_recorded: Callable[[MovementResult], None]) -> None:
        super().__init__(master, corner_radius=10)
        self._view = view
        self._on_recorded = on_recorded
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 6))
        self.movement = ctk.CTkSegmentedButton(top, values=list(MOVEMENTS),
                                               command=lambda _v: self._movement_changed())
        self.movement.set("Stock In")
        self.movement.pack(side="right")
        self.picker = ProductPicker(top, view.theme, view.money)
        self.picker.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self._build_inputs()

    def _build_inputs(self) -> None:
        """Quantity, unit cost, note and the submit button."""
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 12))
        self.quantity = ctk.CTkEntry(row, width=150, placeholder_text="Quantity")
        self.unit_cost = ctk.CTkEntry(row, width=150, placeholder_text="Unit cost (optional)")
        self.note = ctk.CTkEntry(row, width=330, placeholder_text="Reference / note")
        for index, entry in enumerate((self.quantity, self.unit_cost, self.note)):
            entry.pack(side="left", padx=(0 if index == 0 else 8, 0))
        ctk.CTkButton(row, text="Record movement", width=150, command=self.record).pack(
            side="right")

    def _movement_changed(self) -> None:
        """Adapt placeholders and the cost box to the selected movement type."""
        kind = MOVEMENTS[self.movement.get()]
        adjusting = kind == TX_ADJUST
        self.quantity.configure(placeholder_text="Counted quantity" if adjusting else "Quantity")
        self.note.configure(placeholder_text="Reason (required)" if adjusting
                            else "Reference / note")
        self.unit_cost.configure(state="normal" if kind == TX_IN else "disabled")

    def record(self) -> None:
        """Submit the movement; the owning view shows any error and logs it."""
        product = self.picker.selected()
        if product is None:
            self._view.notify("Choose a product first.", "warning")
            return
        label = self.movement.get()
        result = self._view.guarded(f"Stock > {label}",
                                    lambda: self._submit(product, MOVEMENTS[label]))
        if result is not None:
            for entry in (self.quantity, self.unit_cost, self.note):
                entry.delete(0, "end")
            self._on_recorded(result)

    def _submit(self, product: Product, kind: str) -> MovementResult:
        """Call the stock-service method matching the movement type.

        Args:
            product: Product being moved.
            kind: ``IN``, ``OUT`` or ``ADJUST``.

        Returns:
            The stored movement and updated product.

        Raises:
            AppError: Validation or stock-rule failures from the service.
        """
        stock = self._view.services.stock
        if kind == TX_IN:
            return stock.stock_in(product.id, self.quantity.get(), self.unit_cost.get(),
                                  self.note.get())
        if kind == TX_OUT:
            return stock.stock_out(product.id, self.quantity.get(), self.note.get())
        return stock.adjust(product.id, self.quantity.get(), self.note.get())
