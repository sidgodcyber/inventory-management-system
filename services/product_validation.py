"""Poka-Yoke rules for the product form: turn raw input into a valid Product.

Kept separate from :mod:`services.product_service` so the validation rules
can be read, tested and changed without touching the product lifecycle
(create, update, delete, export).

Layer: services
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from config.config_loader import AppConfig
from core.exceptions import ValidationError
from models.product import Product
from repositories.category_repository import CategoryRepository
from repositories.product_repository import ProductRepository
from repositories.supplier_repository import SupplierRepository
from utils.validators import Validator, is_blank


@dataclass
class ProductRepos:
    """Repositories the product rules read from (keeps constructors short).

    Attributes:
        products: Product repository.
        categories: Category repository.
        suppliers: Supplier repository.
    """

    products: ProductRepository
    categories: CategoryRepository
    suppliers: SupplierRepository


class ProductFormParser:
    """Validate product form values field by field.

    Args:
        repos: Repositories used for existence and uniqueness checks.
        validator: Config-driven field validator.
        config: Source of units and the maximum reorder level.
    """

    def __init__(self, repos: ProductRepos, validator: Validator, config: AppConfig) -> None:
        self._repos = repos
        self._validate = validator
        self._config = config

    def units(self) -> list[str]:
        """Units of measure allowed in the form.

        Returns:
            The ``inventory.units`` list from config.
        """
        return list(self._config.get("inventory.units"))

    def parse(self, data: Mapping[str, Any]) -> Product:
        """Turn raw form values into a validated, unsaved :class:`Product`.

        Args:
            data: Form values keyed by product field name.

        Returns:
            A product with clean, typed values (``id`` is ``None``).

        Raises:
            ValidationError: Naming the first invalid field.
        """
        return Product(
            sku=self._validate.sku(data.get("sku")),
            name=self._validate.text(data.get("name"), "Product name"),
            category_id=self._category_id(data.get("category_id")),
            supplier_id=self._supplier_id(data.get("supplier_id")),
            unit=self._validate.choice(data.get("unit"), "Unit", self.units()),
            unit_cost=self._validate.decimal(data.get("unit_cost"), "Unit cost"),
            selling_price=self._validate.decimal(data.get("selling_price"), "Selling price"),
            reorder_level=self._validate.integer(
                data.get("reorder_level"), "Reorder level", minimum=0,
                maximum=self._config.get("validation.reorder_level_max")),
        )

    def opening_quantity(self, value: Any) -> int:
        """Validate optional opening stock.

        Args:
            value: Raw form value; blank means zero.

        Returns:
            A whole number of units, zero or more.

        Raises:
            ValidationError: If the value is not a non-negative whole number.
        """
        return 0 if is_blank(value) else self._validate.integer(value, "Opening stock", minimum=0)

    def ensure_unique_sku(self, sku: str, exclude_id: int | None = None) -> None:
        """Refuse an SKU that another product (even a deactivated one) uses.

        Args:
            sku: Clean SKU to check.
            exclude_id: The product being edited, which may keep its own SKU.

        Raises:
            ValidationError: If the SKU is taken.
        """
        existing = self._repos.products.get_by_sku(sku)
        if existing and existing.id != exclude_id:
            state = "" if existing.is_active else " (deactivated)"
            raise ValidationError(f"SKU {sku} is already used by '{existing.name}'{state}.", "SKU")

    @staticmethod
    def warnings(product: Product) -> list[str]:
        """Non-blocking checks shown after saving.

        Args:
            product: The validated product.

        Returns:
            Messages for the operator, e.g. selling below cost.
        """
        if product.selling_price < product.unit_cost:
            return [f"Selling price is below unit cost for {product.sku}; "
                    "each sale will lose money."]
        return []

    def _category_id(self, value: Any) -> int:
        """Required, existing category id."""
        if is_blank(value):
            raise ValidationError("Please choose a category.", "Category")
        category_id = self._validate.integer(value, "Category", minimum=1)
        if self._repos.categories.get(category_id) is None:
            raise ValidationError("The selected category no longer exists.", "Category")
        return category_id

    def _supplier_id(self, value: Any) -> int | None:
        """Optional, existing supplier id."""
        if is_blank(value):
            return None
        supplier_id = self._validate.integer(value, "Supplier", minimum=1)
        if self._repos.suppliers.get(supplier_id) is None:
            raise ValidationError("The selected supplier no longer exists.", "Supplier")
        return supplier_id
