"""Data access for the ``products`` table, including stock-health queries.

Layer: repositories
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

from models.common import ListQuery, Page
from models.product import EDITABLE_FIELDS, Product
from repositories.base import BaseRepository

_FROM = """
      FROM products p
      JOIN categories c ON c.id = p.category_id
      LEFT JOIN suppliers s ON s.id = p.supplier_id"""

_SELECT = f"SELECT p.*, c.name AS category_name, s.name AS supplier_name {_FROM}"

_LOW_STOCK = "p.quantity_on_hand <= p.reorder_level"


class ProductRepository(BaseRepository):
    """CRUD, search and stock aggregates for products."""

    SORT_COLUMNS = {
        "sku": "p.sku",
        "name": "p.name",
        "category_name": "c.name",
        "supplier_name": "s.name",
        "unit": "p.unit",
        "unit_cost": "p.unit_cost",
        "selling_price": "p.selling_price",
        "quantity_on_hand": "p.quantity_on_hand",
        "reorder_level": "p.reorder_level",
        "stock_value": "p.quantity_on_hand * p.unit_cost",
        "updated_at": "p.updated_at",
    }

    # -- writes -----------------------------------------------------------
    def create(self, product: Product) -> int:
        """Insert a product with zero stock and return its id.

        Opening stock is recorded afterwards as a stock-in transaction, so every
        unit on hand can be traced to a movement.
        """
        now = self.now()
        values = [getattr(product, name) for name in EDITABLE_FIELDS]
        cursor = self.db.execute(
            f"INSERT INTO products ({', '.join(EDITABLE_FIELDS)}, quantity_on_hand, "
            f"is_active, created_at, updated_at) "
            f"VALUES ({', '.join('?' * len(EDITABLE_FIELDS))}, 0, 1, ?, ?)",
            (*values, now, now),
        )
        return int(cursor.lastrowid)

    def update(self, product: Product) -> None:
        """Overwrite the editable fields (never the quantity).

        Args:
            product: Product carrying its ``id`` and the new field values.
        """
        assignments = ", ".join(f"{name} = ?" for name in EDITABLE_FIELDS)
        values = [getattr(product, name) for name in EDITABLE_FIELDS]
        self.db.execute(
            f"UPDATE products SET {assignments}, updated_at = ? WHERE id = ?",
            (*values, self.now(), product.id),
        )

    def set_quantity(self, product_id: int, quantity: int) -> None:
        """Store a new quantity on hand (called only by the stock service).

        Args:
            product_id: Product to update.
            quantity: New, non-negative quantity on hand.
        """
        self.db.execute(
            "UPDATE products SET quantity_on_hand = ?, updated_at = ? WHERE id = ?",
            (quantity, self.now(), product_id),
        )

    def set_active(self, product_id: int, active: bool) -> None:
        """Soft-delete or restore a product.

        Args:
            product_id: Product to update.
            active: ``False`` to deactivate, ``True`` to restore.
        """
        self.db.execute(
            "UPDATE products SET is_active = ?, updated_at = ? WHERE id = ?",
            (int(active), self.now(), product_id),
        )

    def delete(self, product_id: int) -> None:
        """Hard-delete a product that has no transaction history.

        Args:
            product_id: Product to remove permanently.
        """
        self.db.execute("DELETE FROM products WHERE id = ?", (product_id,))

    # -- reads ------------------------------------------------------------
    def get(self, product_id: int) -> Product | None:
        """Load one product with its category and supplier names.

        Args:
            product_id: Primary key.

        Returns:
            The product (active or not), or ``None`` if it does not exist.
        """
        row = self.db.query_one(f"{_SELECT} WHERE p.id = ?", (product_id,))
        return Product.from_row(row) if row else None

    def get_by_sku(self, sku: str) -> Product | None:
        """Find a product by SKU, ignoring letter case.

        Args:
            sku: Stock-keeping code.

        Returns:
            The product (active or not), or ``None``.
        """
        row = self.db.query_one(f"{_SELECT} WHERE p.sku = ?", (sku.strip(),))
        return Product.from_row(row) if row else None

    def find(
        self,
        query: ListQuery,
        category_id: int | None = None,
        low_stock_only: bool = False,
        include_inactive: bool = False,
    ) -> Page[Product]:
        """Search, filter, sort and paginate products.

        Args:
            query: Search text matches SKU, name, category or supplier.
            category_id: Restrict to one category.
            low_stock_only: Only products at or below their reorder level.
            include_inactive: Include soft-deleted products.

        Returns:
            One page of products.
        """
        clauses, params = self._filters(query.search, category_id, low_stock_only, include_inactive)
        where = self.where(clauses)
        return self.paginate(
            f"{_SELECT}{where}", f"SELECT COUNT(*) {_FROM}{where}", params, query, Product.from_row
        )

    def _filters(
        self, search: str, category_id: int | None, low_stock_only: bool, include_inactive: bool
    ) -> tuple[list[str], list[Any]]:
        """Translate filter options into WHERE clauses and parameters."""
        clauses: list[str] = [] if include_inactive else ["p.is_active = 1"]
        params: list[Any] = []
        if search.strip():
            clauses.append("(p.sku LIKE ? OR p.name LIKE ? OR c.name LIKE ? OR s.name LIKE ?)")
            params += [self.like(search)] * 4
        if category_id is not None:
            clauses.append("p.category_id = ?")
            params.append(category_id)
        if low_stock_only:
            clauses.append(_LOW_STOCK)
        return clauses, params

    def list_all(self, active_only: bool = True) -> list[Product]:
        """Return products ordered by name (used by drop-downs and reports).

        Args:
            active_only: Exclude soft-deleted products.

        Returns:
            Products sorted by name.
        """
        where = " WHERE p.is_active = 1" if active_only else ""
        rows = self.db.query_all(f"{_SELECT}{where} ORDER BY p.name")
        return [Product.from_row(row) for row in rows]

    def low_stock(self) -> list[Product]:
        """List products that need reordering.

        Returns:
            Active products at or below their reorder level, most urgent
            (furthest below the level) first.
        """
        rows = self.db.query_all(
            f"{_SELECT} WHERE p.is_active = 1 AND {_LOW_STOCK} "
            "ORDER BY p.quantity_on_hand - p.reorder_level, p.name"
        )
        return [Product.from_row(row) for row in rows]

    def has_transactions(self, product_id: int) -> bool:
        """Check whether a product has stock history (decides soft vs hard delete).

        Args:
            product_id: Product to check.

        Returns:
            ``True`` when at least one stock movement references it.
        """
        return bool(
            self.db.query_value(
                "SELECT EXISTS (SELECT 1 FROM stock_transactions WHERE product_id = ?)",
                (product_id,),
                0,
            )
        )

    # -- aggregates -------------------------------------------------------
    def stock_summary(self) -> dict[str, float]:
        """Headline counts and value across active products.

        Returns:
            ``total_products``, ``total_value``, ``low_stock_count`` and
            ``stockout_count``.
        """
        row = self.db.query_one(
            f"""SELECT COUNT(*)                                            AS total_products,
                       COALESCE(SUM(p.quantity_on_hand * p.unit_cost), 0)  AS total_value,
                       COALESCE(SUM(CASE WHEN {_LOW_STOCK}
                                         THEN 1 ELSE 0 END), 0)            AS low_stock_count,
                       COALESCE(SUM(CASE WHEN p.quantity_on_hand = 0
                                         THEN 1 ELSE 0 END), 0)            AS stockout_count
                  FROM products p WHERE p.is_active = 1"""
        )
        return dict(row)

    def value_by_category(self) -> list[tuple[str, float]]:
        """Total stock value at cost for each category (dashboard bar chart).

        Returns:
            ``[(category name, value), ...]`` for active products, largest first.
        """
        rows = self.db.query_all(
            f"""SELECT c.name AS category, SUM(p.quantity_on_hand * p.unit_cost) AS value
                {_FROM} WHERE p.is_active = 1
                GROUP BY c.id ORDER BY value DESC"""
        )
        return [(row["category"], float(row["value"] or 0)) for row in rows]

    def count_low_stock(self) -> int:
        """Count products at risk of stockout (sidebar badge).

        Returns:
            Number of active products at or below their reorder level.
        """
        return int(
            self.db.query_value(
                f"SELECT COUNT(*) FROM products p WHERE p.is_active = 1 AND {_LOW_STOCK}",
                default=0,
            )
        )
