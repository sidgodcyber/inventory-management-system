"""Activity-log model: one row of the business audit trail.

Layer: models
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from models.common import row_to_kwargs


@dataclass
class ActivityLog:
    """A recorded user or system action.

    Attributes:
        id: Primary key.
        timestamp: When it happened.
        user: Operator name at the time.
        action: One of ``core.constants.ACTIONS``.
        entity: Affected entity type.
        entity_id: Affected record id or key.
        details_json: JSON payload with old/new values or error info.
        level: Logging level name.
    """

    id: int | None = None
    timestamp: str = ""
    user: str = ""
    action: str = ""
    entity: str = ""
    entity_id: str | None = None
    details_json: str = "{}"
    level: str = "INFO"

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> ActivityLog:
        """Build an entry from a database row."""
        return cls(**row_to_kwargs(cls, row))

    @property
    def details(self) -> dict[str, Any]:
        """Decoded details; an unreadable payload becomes ``{"raw": text}``."""
        try:
            decoded = json.loads(self.details_json or "{}")
        except json.JSONDecodeError:
            return {"raw": self.details_json}
        return decoded if isinstance(decoded, dict) else {"value": decoded}

    def to_dict(self) -> dict[str, Any]:
        """Return the fields as a plain dictionary."""
        return asdict(self)
