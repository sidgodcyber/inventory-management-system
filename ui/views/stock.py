"""Stock screen: record stock in / out / adjustments and browse the history.

This screen is the only place an operator can change quantity on hand. Every
movement goes through ``StockService``, which refuses negative stock and
writes the audit entry. The history can be filtered by product, type and
date range, sorted, paged and exported to CSV.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from datetime import date
from typing import Any

import customtkinter as ctk

from core.constants import TRANSACTION_TYPES, TX_ADJUST, TX_IN, TX_OUT
from models.common import ListQuery
from models.filters import TransactionFilter
from models.product import Product
from models.stock_transaction import StockTransaction
from services.stock_service import MovementResult
from ui.components.data_table import TAG_SUCCESS, TAG_WARNING, Column, DataTable, Row
from ui.components.messages import show_info
from ui.views.base_view import BaseView
from utils.validators import Validator

ALL_PRODUCTS = "All products"
ALL_TYPES = "All types"
# Movement selector labels mapped to transaction types.
MOVEMENTS = {"Stock In": TX_IN, "Stock Out": TX_OUT, "Adjust": TX_ADJUST}


class StockView(BaseView):
    """Record movements and view the transaction history."""

    title = "Stock"
    subtitle = ("Receive, issue or adjust stock. Stock can never go negative; "
                "adjustments need a reason. Every movement is audited.")
    columns = (
        Column("created_at", "Date / time", 130),
        Column("product_sku", "SKU", 100),
        Column("product_name", "Product", 200),
        Column("type", "Type", 70, "center"),
        Column("quantity", "Qty", 60, "e"),
        Column("unit_cost", "Unit cost", 85, "e"),
        Column("value", "Value", 95, "e", sortable=False),
        Column("reference_note", "Reference / note", 200, sortable=False),
        Column("performed_by", "By", 100),
    )

    def build(self) -> None:
        """Movement card on top, history below."""
        self._products: dict[str, Product] = {}
        self.query = ListQuery(sort_by="created_at", descending=True,
                               page_size=self.setting("page_size"))
        self.filters = TransactionFilter()
        self._build_movement_card()
        self._build_history_filters()
        self.table = DataTable(self.body, self.theme, self.columns, on_sort=self._on_sort,
                               on_page=self._on_page, height=9)
        self.table.pack(fill="both", expand=True)
        self.table.mark_sorted(self.query.sort_by, self.query.descending)

    # -- movement card ------------------------------------------------------------------
    def _build_movement_card(self) -> None:
        """Product picker, movement type, quantity, cost, note and submit."""
        card = ctk.CTkFrame(self.body, corner_radius=10)
        card.pack(fill="x", pady=(0, 14))
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 6))
        self.product_box = ctk.CTkComboBox(top, values=[""], width=380, font=self.theme.font(),
                                           command=lambda _v: self._update_product_info())
        self.product_box.pack(side="left")
        self.product_box.bind("<KeyRelease>", lambda _e: self._update_product_info())
        self.movement = ctk.CTkSegmentedButton(top, values=list(MOVEMENTS),
                                               command=lambda _v: self._movement_changed())
        self.movement.set("Stock In")
        self.movement.pack(side="left", padx=12)
        self.product_info = ctk.CTkLabel(top, text="", font=self.theme.font(-1),
                                         text_color=self.theme.color("muted"), anchor="w")
        self.product_info.pack(side="left", fill="x", expand=True)
        self._build_movement_inputs(card)

    def _build_movement_inputs(self, card: Any) -> None:
        """Second row of the movement card."""
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 12))
        self.quantity = ctk.CTkEntry(row, width=150, placeholder_text="Quantity")
        self.quantity.pack(side="left")
        self.unit_cost = ctk.CTkEntry(row, width=150, placeholder_text="Unit cost (optional)")
        self.unit_cost.pack(side="left", padx=(8, 0))
        self.note = ctk.CTkEntry(row, width=330, placeholder_text="Reference / note")
        self.note.pack(side="left", padx=(8, 0))
        ctk.CTkButton(row, text="Record movement", width=150,
                      command=self._record).pack(side="right")

    def _movement_changed(self) -> None:
        """Adapt placeholders to the selected movement type."""
        kind = MOVEMENTS[self.movement.get()]
        self.quantity.configure(placeholder_text="Counted quantity" if kind == TX_ADJUST
                                else "Quantity")
        self.note.configure(placeholder_text="Reason (required)" if kind == TX_ADJUST
                            else "Reference / note")
        self.unit_cost.configure(state="normal" if kind == TX_IN else "disabled")

    def _selected_product(self) -> Product | None:
        """Product matching the picker text (full label or just the SKU)."""
        text = self.product_box.get().strip()
        sku = text.split(" — ")[0].upper()
        return self._products.get(text) or next(
            (p for p in self._products.values() if p.sku == sku), None)

    def _update_product_info(self) -> None:
        """Show stock on hand, reorder level and cost for the chosen product."""
        product = self._selected_product()
        if product is None:
            self.product_info.configure(text="Choose a product (type its SKU or pick from the list)")
            return
        warning = "  ⚠ low stock" if product.is_low_stock else ""
        self.product_info.configure(
            text=f"On hand: {product.quantity_on_hand} {product.unit}   ·   Reorder level: "
                 f"{product.reorder_level}   ·   Unit cost: {self.money(product.unit_cost)}"
                 f"{warning}")

    def _record(self) -> None:
        """Validate the picker and submit the movement to the stock service."""
        product = self._selected_product()
        if product is None:
            self.notify("Choose a product first.", "warning")
            return
        label = self.movement.get()
        result = self.guarded(f"Stock > {label}", lambda: self._submit(product, MOVEMENTS[label]))
        if result is not None:
            self._recorded(result, label)

    def _submit(self, product: Product, kind: str) -> MovementResult:
        """Call the right stock-service method for ``kind``."""
        stock = self.services.stock
        if kind == TX_IN:
            return stock.stock_in(product.id, self.quantity.get(), self.unit_cost.get(),
                                  self.note.get())
        if kind == TX_OUT:
            return stock.stock_out(product.id, self.quantity.get(), self.note.get())
        return stock.adjust(product.id, self.quantity.get(), self.note.get())

    def _recorded(self, result: MovementResult, label: str) -> None:
        """Feedback, clear inputs and refresh everything that shows stock."""
        product = result.product
        if result.low_stock_alert:
            self.notify(f"{label} recorded. {product.name} is at or below its reorder level "
                        f"({product.quantity_on_hand} left).", "warning")
        else:
            self.notify(f"{label} recorded: {product.name} now {product.quantity_on_hand}.",
                        "success")
        for entry in (self.quantity, self.unit_cost, self.note):
            entry.delete(0, "end")
        self._load_products(keep=product.id)
        self.refresh_history()
        self.app.refresh_badge()

    # -- history ------------------------------------------------------------------------
    def _build_history_filters(self) -> None:
        """Product, type and date-range filters with apply/clear/export."""
        bar = ctk.CTkFrame(self.body, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(bar, text="History", font=self.theme.font(2, "bold")).pack(side="left")
        self.filter_product = ctk.CTkOptionMenu(bar, values=[ALL_PRODUCTS], width=200,
                                                dynamic_resizing=False)
        self.filter_product.pack(side="left", padx=(14, 0))
        self.filter_type = ctk.CTkOptionMenu(bar, values=[ALL_TYPES, *TRANSACTION_TYPES],
                                             width=110)
        self.filter_type.pack(side="left", padx=(8, 0))
        self.date_from = ctk.CTkEntry(bar, width=140)
        self.date_from.pack(side="left", padx=(8, 0))
        self.date_to = ctk.CTkEntry(bar, width=140)
        self.date_to.pack(side="left", padx=(6, 0))
        for text, command, kind in (("Export CSV", self._export, "transparent"),
                                    ("Clear", self._clear_filters, "transparent"),
                                    ("Apply", self._apply_filters, None)):
            options = {"fg_color": kind, "border_width": 1,
                       "text_color": ("gray10", "gray90")} if kind else {}
            ctk.CTkButton(bar, text=text, width=90, command=command, **options).pack(
                side="right", padx=(6, 0))

    def _read_filters(self) -> TransactionFilter:
        """Build a filter from the widgets (dates use the date-format setting)."""
        fmt = self.setting("date_format")
        product = self._products.get(self.filter_product.get())
        kind = self.filter_type.get()
        return TransactionFilter(
            product_id=product.id if product else None,
            tx_type=None if kind == ALL_TYPES else kind,
            date_from=Validator.date(self.date_from.get(), "From date", fmt),
            date_to=Validator.date(self.date_to.get(), "To date", fmt),
        )

    def _apply_filters(self) -> None:
        """Apply the filter widgets to the history."""
        filters = self.guarded("Stock > Filter history", self._read_filters)
        if filters is not None:
            self.filters, self.query.page = filters, 1
            self.refresh_history()

    def _clear_filters(self) -> None:
        """Reset every history filter."""
        self.filter_product.set(ALL_PRODUCTS)
        self.filter_type.set(ALL_TYPES)
        for entry in (self.date_from, self.date_to):
            entry.delete(0, "end")
        self.filters, self.query.page = TransactionFilter(), 1
        self.refresh_history()

    def _export(self) -> None:
        """Export the filtered history to CSV."""
        path = self.guarded("Stock > Export", lambda: self.services.stock.export_csv(self.filters))
        if path:
            self.notify(f"Exported {path.name}", "success")
            show_info(self, "Export complete", f"Transaction history saved to:\n{path}")

    def _on_sort(self, key: str, descending: bool) -> None:
        """Header clicked."""
        self.query.sort_by, self.query.descending = key, descending
        self.refresh_history()

    def _on_page(self, page: int) -> None:
        """Pager clicked."""
        self.query.page = page
        self.refresh_history()

    def refresh_history(self) -> None:
        """Reload the current history page."""
        self.query.page_size = self.setting("page_size")
        page = self.guarded("Stock > Load history",
                            lambda: self.services.stock.history(self.filters, self.query))
        if page is not None:
            self.table.set_page(page, [self._to_row(tx) for tx in page.items])

    def _to_row(self, tx: StockTransaction) -> Row:
        """Table row; IN in green and ADJUST in amber for quick scanning."""
        tags = {TX_IN: (TAG_SUCCESS,), TX_ADJUST: (TAG_WARNING,)}.get(tx.type, ())
        values = (self.datetime_text(tx.created_at), tx.product_sku, tx.product_name, tx.type,
                  tx.quantity, self.money(tx.unit_cost), self.money(tx.value),
                  tx.reference_note, tx.performed_by)
        return str(tx.id), values, tags

    # -- lifecycle ----------------------------------------------------------------------
    def refresh(self) -> None:
        """Reload products, date hints and the history."""
        self._load_products()
        example = self._date_example()
        self.date_from.configure(placeholder_text=f"From e.g. {example}")
        self.date_to.configure(placeholder_text=f"To e.g. {example}")
        self.refresh_history()

    def _date_example(self) -> str:
        """Today's date in the configured format (shown as a placeholder)."""
        return date.today().strftime(self.setting("date_format"))

    def _load_products(self, keep: int | None = None) -> None:
        """Refresh picker labels (they include stock on hand)."""
        products = self.guarded("Stock > Load products", self.services.products.list_active)
        if products is None:
            return
        self._products = {f"{p.sku} — {p.name}": p for p in products}
        labels = list(self._products)
        self.product_box.configure(values=labels)
        self.filter_product.configure(values=[ALL_PRODUCTS, *labels])
        kept = next((label for label, p in self._products.items() if p.id == keep), None)
        if kept:
            self.product_box.set(kept)
        elif self._selected_product() is None:
            self.product_box.set("")
        self._update_product_info()
