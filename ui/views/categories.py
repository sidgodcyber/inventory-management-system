"""Categories screen: list, search, add, edit and delete product categories.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

from models.category import Category
from models.common import ListQuery, Page
from ui.components.data_table import Column, Row
from ui.components.form_dialog import TEXT, FormField
from ui.views.crud_view import CrudView


class CategoriesView(CrudView):
    """CRUD screen for categories."""

    title = "Categories"
    subtitle = "Group products for reporting. A category in use cannot be deleted."
    entity = "Category"
    search_hint = "Search name or description…"
    columns = (
        Column("name", "Name", 220),
        Column("description", "Description", 420),
        Column("product_count", "Active products", 130, "e"),
        Column("updated_at", "Last updated", 150),
    )

    def fetch(self, query: ListQuery) -> Page[Category]:
        """One page of categories."""
        return self.services.categories.find(query)

    def to_row(self, item: Category) -> Row:
        """Table row for a category."""
        return (str(item.id),
                (item.name, item.description, item.product_count,
                 self.datetime_text(item.updated_at)),
                ())

    def load(self, item_id: int) -> Category:
        """Category to edit."""
        return self.services.categories.get(item_id)

    def form_fields(self, item: Any | None) -> list[FormField]:
        """Name and description."""
        return [FormField("name", "Name", required=True, placeholder="e.g. Stationery"),
                FormField("description", "Description", TEXT)]

    def save(self, values: dict[str, str], item_id: int | None) -> Category:
        """Create or update through the service."""
        service = self.services.categories
        if item_id is None:
            return service.create(values["name"], values["description"])
        return service.update(item_id, values["name"], values["description"])

    def remove(self, item_id: int) -> str:
        """Delete through the service."""
        self.services.categories.delete(item_id)
        return "Category deleted."
