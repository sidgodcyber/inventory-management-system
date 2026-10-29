"""Product form definition: fields, defaults and name ↔ id translation.

Separated from :mod:`ui.views.products` so the screen deals with listing and
filtering while this module knows how a product maps to and from the form.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

from services.container import AppServices
from ui.components.form_fields import COMBO, FormField

NO_SUPPLIER = "— None —"


class ProductForm:
    """Builds the product dialog and converts its values for the service.

    Args:
        services: Service container (categories, suppliers, products, config).
    """

    def __init__(self, services: AppServices) -> None:
        self._services = services
        self.category_ids: dict[str, int] = {}
        self.supplier_ids: dict[str, int] = {}

    def load_lookups(self) -> None:
        """Refresh the category and supplier name-to-id maps."""
        self.category_ids = {c.name: c.id for c in self._services.categories.list_all()}
        self.supplier_ids = {s.name: s.id for s in self._services.suppliers.list_all()}

    def fields(self, adding: bool) -> list[FormField]:
        """Form fields; opening stock is offered only when adding.

        Args:
            adding: ``True`` for the add form, ``False`` for edit.

        Returns:
            Field definitions in display order.
        """
        self.load_lookups()
        fields = [
            FormField("sku", "SKU", required=True, placeholder="e.g. STA-PEN-001",
                      hint="2–20 characters: letters, digits and dashes"),
            FormField("name", "Name", required=True),
            FormField("category", "Category", COMBO, list(self.category_ids), required=True),
            FormField("supplier", "Supplier", COMBO, [NO_SUPPLIER, *self.supplier_ids]),
            FormField("unit", "Unit", COMBO, self._services.products.units(), required=True),
            FormField("unit_cost", "Unit cost", required=True),
            FormField("selling_price", "Selling price", required=True),
            FormField("reorder_level", "Reorder level", required=True,
                      hint="Low-stock alert when stock falls to this level"),
        ]
        if adding:
            fields.append(FormField("opening_quantity", "Opening stock",
                                    hint="Booked as a traceable stock-in transaction"))
        return fields

    def initial(self, item: Any | None) -> dict[str, Any]:
        """Pre-fill values: settings/config defaults when adding, current values when editing.

        Args:
            item: ``None`` when adding, otherwise the product being edited.

        Returns:
            ``{field key: value}``.
        """
        if item is None:
            return {"unit": self._services.config.get("inventory.default_unit"),
                    "reorder_level": self._services.products.default_reorder_level(),
                    "supplier": NO_SUPPLIER}
        return {**vars(item), "category": item.category_name,
                "supplier": item.supplier_name or NO_SUPPLIER}

    def to_data(self, values: dict[str, str]) -> dict[str, Any]:
        """Translate chosen names into the ids the product service expects.

        Args:
            values: Raw dialog values.

        Returns:
            Values with ``category_id`` and ``supplier_id`` added.
        """
        return {**values,
                "category_id": self.category_ids.get(values.get("category", ""), ""),
                "supplier_id": self.supplier_ids.get(values.get("supplier", ""), "")}
