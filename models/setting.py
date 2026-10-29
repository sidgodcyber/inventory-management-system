"""Setting model: one row of the runtime ``settings`` table.

Layer: models
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from models.common import row_to_kwargs


@dataclass
class Setting:
    """A stored runtime setting.

    Attributes:
        key: Setting name (primary key).
        value: Value serialised as text.
        value_type: Declared type (``str``, ``int``, ``float``, ``bool``).
        description: Help text.
        updated_at: Last change timestamp.
    """

    key: str = ""
    value: str = ""
    value_type: str = "str"
    description: str = ""
    updated_at: str = ""

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> Setting:
        """Build a setting from a database row."""
        return cls(**row_to_kwargs(cls, row))

    def to_dict(self) -> dict[str, Any]:
        """Return the fields as a plain dictionary."""
        return asdict(self)
