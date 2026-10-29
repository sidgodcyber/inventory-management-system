"""Suppliers screen: list, search, add, edit and delete suppliers.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

from models.common import ListQuery, Page
from models.supplier import Supplier
from ui.components.data_table import Column, Row
from ui.components.form_dialog import TEXT, FormField
from ui.views.crud_view import CrudView


class SuppliersView(CrudView):
    """CRUD screen for suppliers."""

    title = "Suppliers"
    subtitle = "Vendors that products are purchased from, with contact details."
    entity = "Supplier"
    search_hint = "Search name, contact, phone or email…"
    columns = (
        Column("name", "Supplier", 220),
        Column("contact_person", "Contact person", 160),
        Column("phone", "Phone", 150),
        Column("email", "Email", 220),
        Column("product_count", "Active products", 120, "e"),
    )

    def fetch(self, query: ListQuery) -> Page[Supplier]:
        """One page of suppliers."""
        return self.services.suppliers.find(query)

    def to_row(self, item: Supplier) -> Row:
        """Table row for a supplier."""
        return (str(item.id),
                (item.name, item.contact_person, item.phone, item.email, item.product_count),
                ())

    def load(self, item_id: int) -> Supplier:
        """Supplier to edit."""
        return self.services.suppliers.get(item_id)

    def form_fields(self, item: Any | None) -> list[FormField]:
        """Name and contact details."""
        return [
            FormField("name", "Supplier name", required=True),
            FormField("contact_person", "Contact person"),
            FormField("phone", "Phone", placeholder="+91 98765 43210",
                      hint="7–15 digits; spaces, dashes and a leading + allowed"),
            FormField("email", "Email", placeholder="name@example.com"),
            FormField("address", "Address", TEXT),
        ]

    def save(self, values: dict[str, str], item_id: int | None) -> Supplier:
        """Create or update through the service."""
        if item_id is None:
            return self.services.suppliers.create(values)
        return self.services.suppliers.update(item_id, values)

    def remove(self, item_id: int) -> str:
        """Delete through the service."""
        self.services.suppliers.delete(item_id)
        return "Supplier deleted."
