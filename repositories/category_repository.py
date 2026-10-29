"""Data access for the ``categories`` table.

Layer: repositories
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

from models.category import Category
from models.common import ListQuery, Page
from repositories.base import BaseRepository

_SELECT = """
    SELECT c.*,
           (SELECT COUNT(*) FROM products p
             WHERE p.category_id = c.id AND p.is_active = 1) AS product_count
      FROM categories c"""


class CategoryRepository(BaseRepository):
    """CRUD and search for categories."""

    SORT_COLUMNS = {
        "name": "c.name",
        "description": "c.description",
        "product_count": "product_count",
        "created_at": "c.created_at",
        "updated_at": "c.updated_at",
    }

    def create(self, name: str, description: str) -> int:
        """Insert a category.

        Args:
            name: Unique name.
            description: Optional description.

        Returns:
            The new category id.
        """
        now = self.now()
        cursor = self.db.execute(
            "INSERT INTO categories (name, description, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (name, description, now, now),
        )
        return int(cursor.lastrowid)

    def update(self, category_id: int, name: str, description: str) -> None:
        """Overwrite a category's name and description."""
        self.db.execute(
            "UPDATE categories SET name = ?, description = ?, updated_at = ? WHERE id = ?",
            (name, description, self.now(), category_id),
        )

    def delete(self, category_id: int) -> None:
        """Delete a category (the FK constraint protects referenced rows)."""
        self.db.execute("DELETE FROM categories WHERE id = ?", (category_id,))

    def get(self, category_id: int) -> Category | None:
        """Return one category or ``None``."""
        row = self.db.query_one(f"{_SELECT} WHERE c.id = ?", (category_id,))
        return Category.from_row(row) if row else None

    def get_by_name(self, name: str) -> Category | None:
        """Return the category with this name (case-insensitive) or ``None``."""
        row = self.db.query_one(f"{_SELECT} WHERE c.name = ?", (name.strip(),))
        return Category.from_row(row) if row else None

    def find(self, query: ListQuery) -> Page[Category]:
        """Search, sort and paginate categories.

        Args:
            query: Search text matches name or description.

        Returns:
            One page of categories with their active product counts.
        """
        clauses: list[str] = []
        params: list[Any] = []
        if query.search.strip():
            clauses.append("(c.name LIKE ? OR c.description LIKE ?)")
            params += [self.like(query.search)] * 2
        where = self.where(clauses)
        return self.paginate(
            f"{_SELECT}{where}",
            f"SELECT COUNT(*) FROM categories c{where}",
            params,
            query,
            Category.from_row,
        )

    def list_all(self) -> list[Category]:
        """Return every category ordered by name (for drop-downs)."""
        return [Category.from_row(r) for r in self.db.query_all(f"{_SELECT} ORDER BY c.name")]

    def count_products(self, category_id: int) -> int:
        """Count products (active or soft-deleted) that reference the category."""
        return int(
            self.db.query_value(
                "SELECT COUNT(*) FROM products WHERE category_id = ?", (category_id,), 0
            )
        )
