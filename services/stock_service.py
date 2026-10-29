"""Stock movements: the *only* code path that changes ``quantity_on_hand``.

Each movement (stock in, stock out, adjustment) runs inside one database
transaction that (1) records a ``stock_transactions`` row, (2) updates the
product quantity and (3) writes the audit entry. Either all three happen or
none do. Stock can never go negative: an over-issue raises
:class:`~core.exceptions.StockError` before anything is written.

Layer: services
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from config.config_loader import AppConfig
from core.constants import (
    ACTION_ADJUST,
    ACTION_EXPORT,
    ACTION_STOCK_IN,
    ACTION_STOCK_OUT,
    ENTITY_STOCK,
    TX_ADJUST,
    TX_IN,
    TX_OUT,
)
from core.database import Database
from core.exceptions import NotFoundError, StockError, ValidationError
from core.logger import get_logger, log_activity
from core.settings_manager import SettingsManager
from models.common import ListQuery, Page
from models.filters import TransactionFilter
from models.product import Product
from models.stock_transaction import StockTransaction
from repositories.product_repository import ProductRepository
from repositories.stock_transaction_repository import StockTransactionRepository
from utils.csv_export import default_export_path, write_csv
from utils.date_helpers import to_timestamp
from utils.validators import Validator

_ACTIONS = {TX_IN: ACTION_STOCK_IN, TX_OUT: ACTION_STOCK_OUT, TX_ADJUST: ACTION_ADJUST}

EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("created_at", "Date"),
    ("product_sku", "SKU"),
    ("product_name", "Product"),
    ("type", "Type"),
    ("quantity", "Quantity"),
    ("unit_cost", "Unit cost"),
    ("value", "Value"),
    ("reference_note", "Reference / note"),
    ("performed_by", "Performed by"),
)

_log = get_logger(__name__)


@dataclass
class MovementResult:
    """Outcome of a stock movement.

    Attributes:
        transaction: The stored movement.
        product: The product after the movement.
    """

    transaction: StockTransaction
    product: Product

    @property
    def low_stock_alert(self) -> bool:
        """True when the movement left the product at or below reorder level."""
        return self.product.is_low_stock


@dataclass
class _Movement:
    """Internal description of a validated movement about to be applied."""

    product: Product
    tx_type: str
    delta: int
    unit_cost: float
    note: str
    occurred_at: datetime | None


class StockService:
    """Stock in, stock out, adjustments and movement history.

    Args:
        products: Product repository.
        transactions: Stock transaction repository.
        validator: Field validator.
        settings: Runtime settings (operator name).
        db: Database, used only to open atomic transactions.
        config: Configuration (export folder).
    """

    def __init__(
        self,
        products: ProductRepository,
        transactions: StockTransactionRepository,
        validator: Validator,
        settings: SettingsManager,
        db: Database,
        config: AppConfig,
    ) -> None:
        self._products = products
        self._transactions = transactions
        self._validate = validator
        self._settings = settings
        self._db = db
        self._config = config

    # -- movements --------------------------------------------------------------
    def stock_in(self, product_id: int, quantity: Any, unit_cost: Any = None,
                 note: str = "", occurred_at: datetime | None = None) -> MovementResult:
        """Receive stock.

        Args:
            product_id: Product receiving stock.
            quantity: Units received (whole number >= 1).
            unit_cost: Purchase cost per unit; defaults to the product's cost.
            note: Reference such as an invoice number.
            occurred_at: Back-dated time (imports and seeding); defaults to now.

        Returns:
            The stored movement and updated product.

        Raises:
            ValidationError: If quantity or cost is invalid.
            StockError: If the product is inactive.
        """
        product = self._active_product(product_id)
        qty = self._validate.integer(quantity, "Quantity", minimum=1)
        cost = product.unit_cost if unit_cost in (None, "") else self._validate.decimal(
            unit_cost, "Unit cost")
        return self._apply(_Movement(product, TX_IN, qty, cost, self._validate.notes(note),
                                     occurred_at))

    def stock_out(self, product_id: int, quantity: Any, note: str = "",
                  occurred_at: datetime | None = None) -> MovementResult:
        """Issue stock (sale or consumption).

        Raises:
            ValidationError: If the quantity is invalid.
            StockError: If it exceeds stock on hand or the product is inactive.
        """
        product = self._active_product(product_id)
        qty = self._validate.integer(quantity, "Quantity", minimum=1)
        if qty > product.quantity_on_hand:
            raise StockError(
                f"Cannot issue {qty} {product.unit} of '{product.name}': only "
                f"{product.quantity_on_hand} in stock. Stock can never go negative."
            )
        return self._apply(_Movement(product, TX_OUT, -qty, product.unit_cost,
                                     self._validate.notes(note), occurred_at))

    def adjust(self, product_id: int, counted_quantity: Any, note: str,
               occurred_at: datetime | None = None) -> MovementResult:
        """Correct stock to a physically counted quantity.

        Args:
            product_id: Product being counted.
            counted_quantity: Units actually on the shelf (>= 0).
            note: Mandatory reason (damage, recount, theft...).
            occurred_at: Optional back-dated time.

        Raises:
            ValidationError: If the count is invalid, unchanged or has no reason.
        """
        product = self._active_product(product_id)
        counted = self._validate.integer(counted_quantity, "Counted quantity", minimum=0)
        reason = self._validate.text(note, "Reason")
        delta = counted - product.quantity_on_hand
        if delta == 0:
            raise ValidationError("Counted quantity equals stock on hand; nothing to adjust.")
        return self._apply(_Movement(product, TX_ADJUST, delta, product.unit_cost, reason,
                                     occurred_at))

    # -- history ----------------------------------------------------------------
    def history(self, filters: TransactionFilter, query: ListQuery) -> Page[StockTransaction]:
        """One page of the filtered movement history."""
        return self._transactions.find(filters, query)

    def export_csv(self, filters: TransactionFilter, path: Path | None = None) -> Path:
        """Export the filtered history to CSV and log ``EXPORT``.

        Returns:
            The written file path.
        """
        rows = self._transactions.list_filtered(filters)
        target = path or default_export_path(self._config.resolve_path("paths.export_dir"),
                                             "stock_transactions")
        write_csv([{**tx.to_dict(), "value": tx.value} for tx in rows], EXPORT_COLUMNS, target)
        log_activity(ACTION_EXPORT, ENTITY_STOCK, None, {"file": str(target), "rows": len(rows)})
        return target

    # -- internals --------------------------------------------------------------
    def _active_product(self, product_id: int) -> Product:
        """Load a product that may receive movements."""
        product = self._products.get(product_id)
        if product is None:
            raise NotFoundError(f"Product #{product_id} no longer exists.")
        if not product.is_active:
            raise StockError(f"'{product.name}' is deactivated; restore it before moving stock.")
        return product

    def _apply(self, move: _Movement) -> MovementResult:
        """Write the transaction, new quantity and audit entry atomically."""
        old_qty = move.product.quantity_on_hand
        new_qty = old_qty + move.delta
        if new_qty < 0:  # defence in depth; stock_out already checks this
            raise StockError("Stock can never go negative.")
        tx = StockTransaction(
            product_id=move.product.id, type=move.tx_type,
            quantity=move.delta if move.tx_type == TX_ADJUST else abs(move.delta),
            unit_cost=move.unit_cost, reference_note=move.note,
            performed_by=self._settings.get("operator_name"),
            created_at=to_timestamp(move.occurred_at) if move.occurred_at else "",
        )
        with self._db.transaction():
            tx.id = self._transactions.create(tx)
            self._products.set_quantity(move.product.id, new_qty)
            log_activity(_ACTIONS[move.tx_type], ENTITY_STOCK, tx.id, {
                "product_id": move.product.id, "sku": move.product.sku,
                "quantity": tx.quantity, "unit_cost": tx.unit_cost, "note": tx.reference_note,
                "quantity_on_hand": {"old": old_qty, "new": new_qty},
            })
        return self._result(tx.id)

    def _result(self, tx_id: int) -> MovementResult:
        """Reload the stored movement and product; warn in the file log if low."""
        stored = self._transactions.get(tx_id)
        product = self._products.get(stored.product_id)
        if product.is_low_stock:
            _log.warning("Low stock: %s (%s) has %s, reorder level %s", product.name,
                         product.sku, product.quantity_on_hand, product.reorder_level)
        return MovementResult(stored, product)
