"""Stock transaction model: one IN, OUT or ADJUST movement.

Layer: models
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from models.common import row_to_kwargs


@dataclass
class StockTransaction:
    """A single stock movement.

    Attributes:
        id: Primary key (``None`` until saved).
        product_id: FK to ``products``.
        type: ``IN``, ``OUT`` or ``ADJUST``.
        quantity: Positive for IN/OUT; signed delta for ADJUST.
        unit_cost: Cost per unit at the time of the movement (used for COGS).
        reference_note: Invoice number, reason, etc.
        performed_by: Operator who recorded the movement.
        created_at: When the movement happened.
        product_sku: Joined product SKU (read-only).
        product_name: Joined product name (read-only).
    """

    id: int | None = None
    product_id: int | None = None
    type: str = ""
    quantity: int = 0
    unit_cost: float = 0.0
    reference_note: str = ""
    performed_by: str = ""
    created_at: str = ""
    product_sku: str = ""
    product_name: str = ""

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> StockTransaction:
        """Build a transaction from a database row."""
        return cls(**row_to_kwargs(cls, row))

    @property
    def value(self) -> float:
        """Monetary value of the movement at cost (always positive)."""
        return abs(self.quantity) * self.unit_cost

    def to_dict(self) -> dict[str, Any]:
        """Return the fields as a plain dictionary."""
        return asdict(self)
