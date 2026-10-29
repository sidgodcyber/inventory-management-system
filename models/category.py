"""Category model: a group of related products (e.g. Stationery).

Layer: models
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from models.common import row_to_kwargs


@dataclass
class Category:
    """A product category.

    Attributes:
        id: Primary key (``None`` until saved).
        name: Unique display name.
        description: Optional free text.
        created_at: Creation timestamp (DB format).
        updated_at: Last-update timestamp (DB format).
        product_count: Number of active products (filled by list queries).
    """

    id: int | None = None
    name: str = ""
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    product_count: int = 0

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> Category:
        """Build a category from a database row."""
        return cls(**row_to_kwargs(cls, row))

    def to_dict(self) -> dict[str, Any]:
        """Return the fields as a plain dictionary."""
        return asdict(self)
