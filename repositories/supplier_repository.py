"""Data access for the ``suppliers`` table.

Layer: repositories
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

from models.common import ListQuery, Page
from models.supplier import Supplier
from repositories.base import BaseRepository

_SELECT = """
    SELECT s.*,
           (SELECT COUNT(*) FROM products p
             WHERE p.supplier_id = s.id AND p.is_active = 1) AS product_count
      FROM suppliers s"""

# Columns written by create/update, in a fixed order.
_FIELDS: tuple[str, ...] = ("name", "contact_person", "phone", "email", "address")


class SupplierRepository(BaseRepository):
    """CRUD and search for suppliers."""

    SORT_COLUMNS = {
        "name": "s.name",
        "contact_person": "s.contact_person",
        "phone": "s.phone",
        "email": "s.email",
        "product_count": "product_count",
        "updated_at": "s.updated_at",
    }

    def create(self, supplier: Supplier) -> int:
        """Insert a supplier and return its new id."""
        now = self.now()
        values = [getattr(supplier, name) for name in _FIELDS]
        cursor = self.db.execute(
            f"INSERT INTO suppliers ({', '.join(_FIELDS)}, created_at, updated_at) "
            f"VALUES ({', '.join('?' * len(_FIELDS))}, ?, ?)",
            (*values, now, now),
        )
        return int(cursor.lastrowid)

    def update(self, supplier: Supplier) -> None:
        """Overwrite every editable column of an existing supplier."""
        assignments = ", ".join(f"{name} = ?" for name in _FIELDS)
        values = [getattr(supplier, name) for name in _FIELDS]
        self.db.execute(
            f"UPDATE suppliers SET {assignments}, updated_at = ? WHERE id = ?",
            (*values, self.now(), supplier.id),
        )

    def delete(self, supplier_id: int) -> None:
        """Delete a supplier (the FK constraint protects referenced rows)."""
        self.db.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))

    def get(self, supplier_id: int) -> Supplier | None:
        """Return one supplier or ``None``."""
        row = self.db.query_one(f"{_SELECT} WHERE s.id = ?", (supplier_id,))
        return Supplier.from_row(row) if row else None

    def find(self, query: ListQuery) -> Page[Supplier]:
        """Search (name, contact, phone, email), sort and paginate suppliers."""
        clauses: list[str] = []
        params: list[Any] = []
        if query.search.strip():
            clauses.append(
                "(s.name LIKE ? OR s.contact_person LIKE ? OR s.phone LIKE ? OR s.email LIKE ?)"
            )
            params += [self.like(query.search)] * 4
        where = self.where(clauses)
        return self.paginate(
            f"{_SELECT}{where}",
            f"SELECT COUNT(*) FROM suppliers s{where}",
            params,
            query,
            Supplier.from_row,
        )

    def list_all(self) -> list[Supplier]:
        """Return every supplier ordered by name (for drop-downs)."""
        return [Supplier.from_row(r) for r in self.db.query_all(f"{_SELECT} ORDER BY s.name")]

    def count_products(self, supplier_id: int) -> int:
        """Count products (active or soft-deleted) that reference the supplier."""
        return int(
            self.db.query_value(
                "SELECT COUNT(*) FROM products WHERE supplier_id = ?", (supplier_id,), 0
            )
        )
