"""Stock screen: record stock in / out / adjustments and browse the history.

This screen is the only place an operator can change quantity on hand. Every
movement goes through ``StockService`` (via :class:`MovementPanel`), which
refuses negative stock and writes the audit entry. The history below can be
filtered by product, type and date range, sorted, paged and exported.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from datetime import date

from core.constants import TX_ADJUST, TX_IN
from models.common import ListQuery, Page
from models.filters import TransactionFilter
from models.movement import MovementResult
from models.product import Product
from models.stock_transaction import StockTransaction
from ui.components.data_table import TAG_SUCCESS, TAG_WARNING, Column, Row
from ui.components.messages import show_info
from ui.components.product_picker import product_label
from ui.views.history_filters import HistoryFilterBar
from ui.views.list_view import ListView
from ui.views.stock_movement import MOVEMENT_LABELS, MovementPanel


class StockView(ListView):
    """Movement panel above a filterable transaction history."""

    title = "Stock"
    subtitle = ("Receive, issue or adjust stock. Stock can never go negative; "
                "adjustments need a reason. Every movement is audited.")
    default_sort = "created_at"
    default_descending = True
    table_height = 9
    columns = (
        Column("created_at", "Date / time", 130), Column("product_sku", "SKU", 100),
        Column("product_name", "Product", 200), Column("type", "Type", 70, "center"),
        Column("quantity", "Qty", 60, "e"), Column("unit_cost", "Unit cost", 85, "e"),
        Column("value", "Value", 95, "e", sortable=False),
        Column("reference_note", "Reference / note", 200, sortable=False),
        Column("performed_by", "By", 100),
    )

    def build(self) -> None:
        """Initialise filter state, then the list layout."""
        self.filters = TransactionFilter()
        self._products: dict[str, Product] = {}
        super().build()

    def build_above_table(self) -> None:
        """Movement panel and history filter bar."""
        self.panel = MovementPanel(self.body, self, on_recorded=self._recorded)
        self.panel.pack(fill="x", pady=(0, 14))
        self.history_filters = HistoryFilterBar(self.body, self.theme, self._apply_filters,
                                                self._filters_cleared, self._export)
        self.history_filters.pack(fill="x", pady=(0, 8))

    # -- ListView hooks -----------------------------------------------------------------
    def fetch(self, query: ListQuery) -> Page[StockTransaction]:
        """One page of the filtered history.

        Args:
            query: Sort and page.

        Returns:
            The requested page of movements.
        """
        return self.services.stock.history(self.filters, query)

    def to_row(self, item: StockTransaction) -> Row:
        """Table row; IN in green and ADJUST in amber for quick scanning.

        Args:
            item: Movement to display.

        Returns:
            ``(row id, values, tags)``.
        """
        tags = {TX_IN: (TAG_SUCCESS,), TX_ADJUST: (TAG_WARNING,)}.get(item.type, ())
        values = (self.datetime_text(item.created_at), item.product_sku, item.product_name,
                  item.type, item.quantity, self.money(item.unit_cost), self.money(item.value),
                  item.reference_note, item.performed_by)
        return str(item.id), values, tags

    def refresh(self) -> None:
        """Reload products (labels show stock), the date hint and the history."""
        self._load_products()
        self.history_filters.set_date_hint(date.today().strftime(self.setting("date_format")))
        self.load_page()

    # -- events -------------------------------------------------------------------------
    def _recorded(self, result: MovementResult) -> None:
        """Toast (warning when now low on stock) and refresh everything showing stock."""
        product, label = result.product, MOVEMENT_LABELS[result.transaction.type]
        if result.low_stock_alert:
            self.notify(f"{label} recorded. {product.name} is at or below its reorder level "
                        f"({product.quantity_on_hand} left).", "warning")
        else:
            self.notify(f"{label} recorded: {product.name} now {product.quantity_on_hand}.",
                        "success")
        self._load_products(keep_id=product.id)
        self.load_page()
        self.app.refresh_badge()

    def _apply_filters(self) -> None:
        """Read the filter bar and show page 1."""
        filters = self.guarded("Stock > Filter history", lambda: self.history_filters.read(
            self._products, self.setting("date_format")))
        if filters is not None:
            self.filters = filters
            self.first_page()

    def _filters_cleared(self) -> None:
        """Drop every history filter."""
        self.filters = TransactionFilter()
        self.first_page()

    def _export(self) -> None:
        """Export the filtered history to CSV."""
        path = self.guarded("Stock > Export", lambda: self.services.stock.export_csv(self.filters))
        if path:
            self.notify(f"Exported {path.name}", "success")
            show_info(self, "Export complete", f"Transaction history saved to:\n{path}")

    def _load_products(self, keep_id: int | None = None) -> None:
        """Refresh product labels in the panel and the filter."""
        products = self.guarded("Stock > Load products", self.services.products.list_active)
        if products is not None:
            self._products = {product_label(p): p for p in products}
            self.panel.picker.set_products(products, keep_id)
            self.history_filters.set_products(list(self._products))
