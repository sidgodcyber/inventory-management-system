"""Product lifecycle: create (with opening stock), update, soft delete, restore, export.

Field-level validation lives in :mod:`services.product_validation`; this module
applies the business workflow around it and writes the audit trail.

Layer: services
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config.config_loader import AppConfig
from core.constants import (
    ACTION_CREATE,
    ACTION_DELETE,
    ACTION_EXPORT,
    ACTION_UPDATE,
    ENTITY_PRODUCT,
)
from core.database import Database
from core.exceptions import NotFoundError
from core.logger import diff_changes, log_activity
from core.settings_manager import SettingsManager
from models.common import ListQuery, Page
from models.product import Product
from services.product_validation import ProductFormParser, ProductRepos
from services.stock_service import StockService
from utils.csv_export import default_export_path, write_csv
from utils.validators import Validator

__all__ = ["EXPORT_COLUMNS", "ProductRepos", "ProductService", "SaveResult"]

EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("sku", "SKU"), ("name", "Name"), ("category_name", "Category"),
    ("supplier_name", "Supplier"), ("unit", "Unit"), ("unit_cost", "Unit cost"),
    ("selling_price", "Selling price"), ("quantity_on_hand", "On hand"),
    ("reorder_level", "Reorder level"), ("stock_value", "Stock value"), ("status", "Status"),
)


@dataclass
class SaveResult:
    """A saved product plus non-blocking warnings for the operator.

    Attributes:
        product: The stored product.
        warnings: Messages such as "selling price is below cost".
    """

    product: Product
    warnings: list[str] = field(default_factory=list)


class ProductService:
    """Create, update, (soft) delete, search and export products.

    Args:
        repos: Product, category and supplier repositories.
        stock: Stock service, used to book opening stock as a stock-in.
        validator: Field validator.
        settings: Runtime settings (default reorder level).
        db: Database, used only to open atomic transactions.
        config: Configuration (units, export folder, limits).
    """

    def __init__(self, repos: ProductRepos, stock: StockService, validator: Validator,
                 settings: SettingsManager, db: Database, config: AppConfig) -> None:
        self._products = repos.products
        self._rules = ProductFormParser(repos, validator, config)
        self._stock = stock
        self._settings = settings
        self._db = db
        self._config = config

    # -- queries ------------------------------------------------------------------
    def find(self, query: ListQuery, category_id: int | None = None,
             low_stock_only: bool = False, include_inactive: bool = False) -> Page[Product]:
        """Search, filter, sort and paginate products.

        Args:
            query: Search text, sort and page.
            category_id: Restrict to one category.
            low_stock_only: Only products at or below reorder level.
            include_inactive: Include soft-deleted products.

        Returns:
            One page of products.
        """
        return self._products.find(query, category_id, low_stock_only, include_inactive)

    def get(self, product_id: int) -> Product:
        """Load a product (active or not).

        Args:
            product_id: Primary key.

        Returns:
            The product.

        Raises:
            NotFoundError: If it does not exist.
        """
        product = self._products.get(product_id)
        if product is None:
            raise NotFoundError(f"Product #{product_id} no longer exists.")
        return product

    def list_active(self) -> list[Product]:
        """Active products ordered by name.

        Returns:
            Products for drop-downs and pickers.
        """
        return self._products.list_all(active_only=True)

    def low_stock_count(self) -> int:
        """Count products at or below reorder level.

        Returns:
            The number shown on the sidebar badge.
        """
        return self._products.count_low_stock()

    def default_reorder_level(self) -> int:
        """Reorder level pre-filled for new products.

        Returns:
            The ``default_reorder_level`` runtime setting.
        """
        return int(self._settings.get("default_reorder_level"))

    def units(self) -> list[str]:
        """Units of measure offered in the product form.

        Returns:
            The configured unit list.
        """
        return self._rules.units()

    # -- commands -----------------------------------------------------------------
    def create(self, data: Mapping[str, Any]) -> SaveResult:
        """Validate and create a product, then book any opening stock.

        Args:
            data: Form values: ``sku``, ``name``, ``category_id``, ``supplier_id``,
                ``unit``, ``unit_cost``, ``selling_price``, ``reorder_level`` and
                optional ``opening_quantity``.

        Returns:
            The stored product and any warnings.

        Raises:
            ValidationError: If any field is invalid or the SKU is taken.
        """
        product = self._rules.parse(data)
        opening = self._rules.opening_quantity(data.get("opening_quantity"))
        self._rules.ensure_unique_sku(product.sku)
        with self._db.transaction():
            product.id = self._products.create(product)
            log_activity(ACTION_CREATE, ENTITY_PRODUCT, product.id,
                         {"new": product.editable_values()})
            if opening:
                self._stock.stock_in(product.id, opening, note="Opening stock")
        return SaveResult(self.get(product.id), self._rules.warnings(product))

    def update(self, product_id: int, data: Mapping[str, Any]) -> SaveResult:
        """Validate and update the editable fields, logging old -> new.

        Args:
            product_id: Product to update.
            data: Form values (quantity is ignored; it changes only via stock).

        Returns:
            The stored product and any warnings.

        Raises:
            NotFoundError: If the product does not exist.
            ValidationError: If any field is invalid or the SKU is taken.
        """
        current = self.get(product_id)
        product = self._rules.parse(data)
        product.id = product_id
        self._rules.ensure_unique_sku(product.sku, exclude_id=product_id)
        changes = diff_changes(current.editable_values(), product.editable_values())
        if changes:
            with self._db.transaction():
                self._products.update(product)
                log_activity(ACTION_UPDATE, ENTITY_PRODUCT, product_id, {"changes": changes})
        return SaveResult(self.get(product_id), self._rules.warnings(product))

    def delete(self, product_id: int) -> str:
        """Delete a product; soft-delete when it has transaction history.

        Args:
            product_id: Product to delete.

        Returns:
            ``"deactivated"`` (soft delete) or ``"deleted"`` (hard delete).
        """
        product = self.get(product_id)
        soft = self._products.has_transactions(product_id)
        with self._db.transaction():
            if soft:
                self._products.set_active(product_id, False)
            else:
                self._products.delete(product_id)
            log_activity(ACTION_DELETE, ENTITY_PRODUCT, product_id,
                         {"old": product.editable_values(), "soft_delete": soft})
        return "deactivated" if soft else "deleted"

    def restore(self, product_id: int) -> Product:
        """Re-activate a soft-deleted product, logging the change.

        Args:
            product_id: Product to restore.

        Returns:
            The product after restoring.
        """
        product = self.get(product_id)
        if not product.is_active:
            with self._db.transaction():
                self._products.set_active(product_id, True)
                log_activity(ACTION_UPDATE, ENTITY_PRODUCT, product_id,
                             {"changes": {"is_active": {"old": False, "new": True}}})
        return self.get(product_id)

    def export_csv(self, include_inactive: bool = False, path: Path | None = None) -> Path:
        """Export the product list to CSV and log ``EXPORT``.

        Args:
            include_inactive: Also export soft-deleted products.
            path: Destination; defaults to a timestamped file in the export folder.

        Returns:
            The written file path.
        """
        products = self._products.list_all(active_only=not include_inactive)
        rows = [{**p.to_dict(), "stock_value": round(p.stock_value, 2), "status": p.status}
                for p in products]
        target = path or default_export_path(self._config.resolve_path("paths.export_dir"),
                                             "products")
        write_csv(rows, EXPORT_COLUMNS, target)
        log_activity(ACTION_EXPORT, ENTITY_PRODUCT, None, {"file": str(target), "rows": len(rows)})
        return target
