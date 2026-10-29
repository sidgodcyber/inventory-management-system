"""Product model with derived stock-health properties.

Layer: models
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from models.common import row_to_kwargs

# Fields a user may edit through the product form. Quantity is deliberately
# excluded: it changes only through stock transactions.
EDITABLE_FIELDS: tuple[str, ...] = (
    "sku",
    "name",
    "category_id",
    "supplier_id",
    "unit",
    "unit_cost",
    "selling_price",
    "reorder_level",
)


@dataclass
class Product:
    """A stock-keeping unit.

    Attributes:
        id: Primary key (``None`` until saved).
        sku: Unique stock-keeping code.
        name: Display name.
        category_id: FK to ``categories``.
        supplier_id: Optional FK to ``suppliers``.
        unit: Unit of measure (pcs, kg, ...).
        unit_cost: Purchase cost per unit.
        selling_price: Sale price per unit.
        quantity_on_hand: Current stock (changed only by stock transactions).
        reorder_level: Low-stock threshold for this product.
        is_active: ``False`` once soft-deleted.
        created_at: Creation timestamp.
        updated_at: Last-update timestamp.
        category_name: Joined category name (read-only).
        supplier_name: Joined supplier name (read-only).
    """

    id: int | None = None
    sku: str = ""
    name: str = ""
    category_id: int | None = None
    supplier_id: int | None = None
    unit: str = ""
    unit_cost: float = 0.0
    selling_price: float = 0.0
    quantity_on_hand: int = 0
    reorder_level: int = 0
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""
    category_name: str = ""
    supplier_name: str = ""

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> Product:
        """Build a product from a database row (SQLite stores booleans as 0/1)."""
        product = cls(**row_to_kwargs(cls, row))
        product.is_active = bool(product.is_active)
        product.supplier_name = product.supplier_name or ""
        return product

    @property
    def is_low_stock(self) -> bool:
        """True when stock is at or below the reorder level (stockout risk)."""
        return self.quantity_on_hand <= self.reorder_level

    @property
    def is_out_of_stock(self) -> bool:
        """True when no stock is left (a stockout)."""
        return self.quantity_on_hand == 0

    @property
    def stock_value(self) -> float:
        """Inventory value at cost: quantity x unit cost."""
        return self.quantity_on_hand * self.unit_cost

    def editable_values(self) -> dict[str, Any]:
        """Return only the user-editable fields (used for old/new audit diffs)."""
        return {name: getattr(self, name) for name in EDITABLE_FIELDS}

    def to_dict(self) -> dict[str, Any]:
        """Return the fields as a plain dictionary."""
        return asdict(self)
