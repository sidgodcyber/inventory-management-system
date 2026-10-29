"""Products screen: CRUD plus low-stock highlighting, filters, restore and export.

Rows at or below their reorder level are shaded red (stockouts darker), so
stockout risk is visible at a glance. That supports the baseline TQM goal
of eliminating stockouts. The form itself is defined in
:mod:`ui.views.product_form`.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from models.common import ListQuery, Page
from models.product import Product
from services.product_service import SaveResult
from ui.components.data_table import TAG_INACTIVE, TAG_LOW, TAG_STOCKOUT, Column, Row
from ui.components.form_dialog import FormField
from ui.components.messages import show_info
from ui.views.crud_view import CrudView
from ui.views.product_form import ProductForm

ALL_CATEGORIES = "All categories"


class ProductsView(CrudView):
    """CRUD screen for products with stock-health cues."""

    title = "Products"
    subtitle = ("Red rows are at or below their reorder level; dark red rows are out of stock. "
                "Quantities change only through the Stock screen.")
    entity = "Product"
    search_hint = "Search SKU, name, category or supplier…"
    columns = (
        Column("sku", "SKU", 100), Column("name", "Name", 190),
        Column("category_name", "Category", 115), Column("supplier_name", "Supplier", 140),
        Column("unit", "Unit", 50, "center"), Column("unit_cost", "Cost", 80, "e"),
        Column("selling_price", "Price", 80, "e"), Column("quantity_on_hand", "On hand", 70, "e"),
        Column("reorder_level", "Reorder", 65, "e"), Column("stock_value", "Value", 95, "e"),
        Column("status", "Status", 80, "center", sortable=False),
    )

    def build(self) -> None:
        """Create the form helper and filter state, then the standard layout."""
        self.form = ProductForm(self.services)
        self.low_only = ctk.BooleanVar(value=False)
        self.show_inactive = ctk.BooleanVar(value=False)
        super().build()

    def add_buttons(self) -> None:
        """Export and restore in addition to add/edit/delete."""
        self.toolbar.add_button("Export CSV", self._export, "secondary", width=100)
        self.toolbar.add_button("Restore", self._restore, "secondary", width=80)
        super().add_buttons()

    def build_filters(self, frame: Any) -> None:
        """Category drop-down and low-stock / inactive toggles.

        Args:
            frame: Filter row container.
        """
        ctk.CTkLabel(frame, text="Filter:", font=self.theme.font(-1)).pack(side="left",
                                                                            padx=(0, 8))
        self.category_filter = ctk.CTkOptionMenu(frame, values=[ALL_CATEGORIES], width=170,
                                                 dynamic_resizing=False,
                                                 command=lambda _v: self.first_page())
        self.category_filter.pack(side="left")
        for text, variable in (("Low stock only", self.low_only),
                               ("Show inactive", self.show_inactive)):
            ctk.CTkCheckBox(frame, text=text, variable=variable, font=self.theme.font(-1),
                            command=self.first_page).pack(side="left", padx=(16, 0))

    def on_show(self) -> None:
        """Reload category choices (they may have changed), then the list."""
        self.form.load_lookups()
        names = [ALL_CATEGORIES, *self.form.category_ids]
        self.category_filter.configure(values=names)
        if self.category_filter.get() not in names:
            self.category_filter.set(ALL_CATEGORIES)
        super().on_show()

    def show_low_stock(self) -> None:
        """Preset the low-stock filter (used by the dashboard shortcut)."""
        self.low_only.set(True)
        self.query.page = 1

    # -- CrudView hooks ---------------------------------------------------------------
    def fetch(self, query: ListQuery) -> Page[Product]:
        """One page of products with the current filters.

        Args:
            query: Search, sort and page.

        Returns:
            The requested page.
        """
        category = self.form.category_ids.get(self.category_filter.get())
        return self.services.products.find(query, category, self.low_only.get(),
                                           self.show_inactive.get())

    def to_row(self, item: Product) -> Row:
        """Table row with money formatting and stock-health tags.

        Args:
            item: Product to display.

        Returns:
            ``(row id, values, tags)``.
        """
        values = (item.sku, item.name, item.category_name, item.supplier_name or "—", item.unit,
                  self.money(item.unit_cost), self.money(item.selling_price),
                  item.quantity_on_hand, item.reorder_level, self.money(item.stock_value),
                  item.status)
        return str(item.id), values, _tags(item)

    def load(self, item_id: int) -> Product:
        """Product to edit (see :meth:`CrudView.load`)."""
        return self.services.products.get(item_id)

    def form_fields(self, item: Any | None) -> list[FormField]:
        """Product form fields (see :class:`ProductForm`)."""
        return self.form.fields(adding=item is None)

    def initial_values(self, item: Any | None) -> dict[str, Any]:
        """Product form defaults (see :class:`ProductForm`)."""
        return self.form.initial(item)

    def save(self, values: dict[str, str], item_id: int | None) -> SaveResult:
        """Create or update through the product service.

        Args:
            values: Dialog values (category and supplier by name).
            item_id: ``None`` to create, otherwise the product to update.

        Returns:
            The saved product and any warnings.
        """
        data = self.form.to_data(values)
        if item_id is None:
            return self.services.products.create(data)
        return self.services.products.update(item_id, data)

    def after_save(self, result: SaveResult) -> None:
        """Show price warnings, otherwise a success toast.

        Args:
            result: Saved product and warnings.
        """
        if result.warnings:
            self.notify(" ".join(result.warnings), "warning")
        else:
            self.notify(f"Product {result.product.sku} saved.", "success")

    def remove(self, item_id: int) -> str:
        """Delete or deactivate through the service.

        Args:
            item_id: Product to delete.

        Returns:
            Status-bar message explaining what happened.
        """
        if self.services.products.delete(item_id) == "deactivated":
            return "Product deactivated: it has stock history. Tick 'Show inactive' to restore it."
        return "Product deleted."

    # -- extra actions ----------------------------------------------------------------
    def _restore(self) -> None:
        """Re-activate the selected product."""
        row_id = self._require_selection("restore")
        if row_id and self.guarded("Products > Restore",
                                   lambda: self.services.products.restore(int(row_id))):
            self.notify("Product restored.", "success")
            self.load_page()
            self.app.refresh_badge()

    def _export(self) -> None:
        """Export the product list to CSV."""
        path = self.guarded("Products > Export", lambda: self.services.products.export_csv(
            include_inactive=self.show_inactive.get()))
        if path:
            self.notify(f"Exported {path.name}", "success")
            show_info(self, "Export complete", f"Product list saved to:\n{path}")


def _tags(product: Product) -> tuple[str, ...]:
    """Row tags for stock health."""
    if not product.is_active:
        return (TAG_INACTIVE,)
    if product.is_out_of_stock:
        return (TAG_STOCKOUT,)
    return (TAG_LOW,) if product.is_low_stock else ()
