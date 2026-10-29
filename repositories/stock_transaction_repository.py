"""Data access for ``stock_transactions`` plus the queries behind turnover maths.

Layer: repositories
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

from core.constants import TX_IN, TX_OUT
from models.common import ListQuery, Page
from models.filters import TransactionFilter
from models.stock_transaction import StockTransaction
from repositories.base import BaseRepository

_FROM = " FROM stock_transactions t JOIN products p ON p.id = t.product_id"
_SELECT = f"SELECT t.*, p.sku AS product_sku, p.name AS product_name{_FROM}"

# Signed effect of a row on quantity_on_hand: OUT subtracts, IN/ADJUST add.
_SIGNED_QTY = f"CASE t.type WHEN '{TX_OUT}' THEN -t.quantity ELSE t.quantity END"


class StockTransactionRepository(BaseRepository):
    """Persistence and aggregate queries for stock movements."""

    SORT_COLUMNS = {
        "created_at": "t.created_at",
        "product_sku": "p.sku",
        "product_name": "p.name",
        "type": "t.type",
        "quantity": "t.quantity",
        "unit_cost": "t.unit_cost",
        "performed_by": "t.performed_by",
    }
    DEFAULT_SORT = "created_at"

    def create(self, tx: StockTransaction) -> int:
        """Insert a movement; ``created_at`` defaults to now when blank.

        Args:
            tx: The movement to store (``id`` is ignored).

        Returns:
            The new transaction id.
        """
        cursor = self.db.execute(
            "INSERT INTO stock_transactions "
            "(product_id, type, quantity, unit_cost, reference_note, performed_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tx.product_id, tx.type, tx.quantity, tx.unit_cost,
             tx.reference_note, tx.performed_by, tx.created_at or self.now()),
        )
        return int(cursor.lastrowid)

    def get(self, tx_id: int) -> StockTransaction | None:
        """Return one movement or ``None``."""
        row = self.db.query_one(f"{_SELECT} WHERE t.id = ?", (tx_id,))
        return StockTransaction.from_row(row) if row else None

    def find(self, filters: TransactionFilter, query: ListQuery) -> Page[StockTransaction]:
        """Filter, sort and paginate the movement history."""
        clauses, params = self._filters(filters, query.search)
        where = self.where(clauses)
        return self.paginate(
            f"{_SELECT}{where}", f"SELECT COUNT(*){_FROM}{where}",
            params, query, StockTransaction.from_row,
        )

    def list_filtered(self, filters: TransactionFilter) -> list[StockTransaction]:
        """Every movement matching ``filters``, newest first (for CSV export)."""
        clauses, params = self._filters(filters, "")
        rows = self.db.query_all(
            f"{_SELECT}{self.where(clauses)} ORDER BY t.created_at DESC, t.id DESC", params
        )
        return [StockTransaction.from_row(row) for row in rows]

    def _filters(self, filters: TransactionFilter, search: str) -> tuple[list[str], list[Any]]:
        """Translate a :class:`TransactionFilter` into WHERE clauses."""
        conditions: list[tuple[bool, str, Any]] = [
            (filters.product_id is not None, "t.product_id = ?", filters.product_id),
            (bool(filters.tx_type), "t.type = ?", filters.tx_type),
            (filters.date_from is not None, "t.created_at >= ?",
             filters.date_from and self.day_start(filters.date_from)),
            (filters.date_to is not None, "t.created_at <= ?",
             filters.date_to and self.day_end(filters.date_to)),
        ]
        clauses = [sql for active, sql, _ in conditions if active]
        params = [value for active, _, value in conditions if active]
        if search.strip():
            clauses.append("(p.sku LIKE ? OR p.name LIKE ? OR t.reference_note LIKE ?)")
            params += [self.like(search)] * 3
        return clauses, params

    # -- aggregates for analytics -----------------------------------------------
    def issues_by_product(self, start: str, end: str) -> dict[int, tuple[int, float]]:
        """Units issued and COGS per product between two timestamps.

        Args:
            start: Inclusive lower bound (DB timestamp).
            end: Inclusive upper bound (DB timestamp).

        Returns:
            ``{product_id: (units_out, cogs)}`` where COGS = sum(qty x unit_cost).
        """
        rows = self.db.query_all(
            f"""SELECT t.product_id, SUM(t.quantity) AS units,
                       SUM(t.quantity * t.unit_cost) AS cogs
                  FROM stock_transactions t
                 WHERE t.type = '{TX_OUT}' AND t.created_at BETWEEN ? AND ?
                 GROUP BY t.product_id""",
            (start, end),
        )
        return {row["product_id"]: (int(row["units"]), float(row["cogs"])) for row in rows}

    def net_change_after(self, since: str) -> dict[int, int]:
        """Signed quantity change per product for movements after ``since``.

        Subtracting this from the current quantity reconstructs the opening
        stock at ``since``, which is needed for average inventory value.
        """
        rows = self.db.query_all(
            f"""SELECT t.product_id, SUM({_SIGNED_QTY}) AS delta
                  FROM stock_transactions t WHERE t.created_at > ?
                 GROUP BY t.product_id""",
            (since,),
        )
        return {row["product_id"]: int(row["delta"]) for row in rows}

    def daily_net_change(self, start: str, end: str) -> list[tuple[int, str, int]]:
        """Signed quantity change per product per day between two timestamps.

        Returns:
            ``[(product_id, YYYY-MM-DD, delta), ...]``; used to rebuild the
            daily closing stock for average inventory value.
        """
        rows = self.db.query_all(
            f"""SELECT t.product_id, substr(t.created_at, 1, 10) AS day,
                       SUM({_SIGNED_QTY}) AS delta
                  FROM stock_transactions t WHERE t.created_at BETWEEN ? AND ?
                 GROUP BY t.product_id, day ORDER BY day""",
            (start, end),
        )
        return [(row["product_id"], row["day"], int(row["delta"])) for row in rows]

    def daily_totals(self, start: str, end: str) -> list[tuple[str, str, int]]:
        """Units moved IN and OUT per calendar day (adjustments excluded).

        Returns:
            ``[(YYYY-MM-DD, type, units), ...]`` ordered by day.
        """
        rows = self.db.query_all(
            f"""SELECT substr(t.created_at, 1, 10) AS day, t.type, SUM(t.quantity) AS units
                  FROM stock_transactions t
                 WHERE t.type IN ('{TX_IN}', '{TX_OUT}') AND t.created_at BETWEEN ? AND ?
                 GROUP BY day, t.type ORDER BY day""",
            (start, end),
        )
        return [(row["day"], row["type"], int(row["units"])) for row in rows]

    def count_for_product(self, product_id: int) -> int:
        """Number of movements recorded for a product."""
        return int(
            self.db.query_value(
                "SELECT COUNT(*) FROM stock_transactions WHERE product_id = ?", (product_id,), 0
            )
        )
