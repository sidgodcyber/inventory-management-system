"""Supplier model: a vendor that products are purchased from.

Layer: models
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from models.common import row_to_kwargs


@dataclass
class Supplier:
    """A supplier and its contact details.

    Attributes:
        id: Primary key (``None`` until saved).
        name: Company name.
        contact_person: Person to call.
        phone: Phone number.
        email: Email address.
        address: Postal address.
        created_at: Creation timestamp.
        updated_at: Last-update timestamp.
        product_count: Number of active products supplied (filled by list queries).
    """

    id: int | None = None
    name: str = ""
    contact_person: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    created_at: str = ""
    updated_at: str = ""
    product_count: int = 0

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> Supplier:
        """Build a supplier from a database row."""
        return cls(**row_to_kwargs(cls, row))

    def to_dict(self) -> dict[str, Any]:
        """Return the fields as a plain dictionary."""
        return asdict(self)
