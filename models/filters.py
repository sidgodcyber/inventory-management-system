"""Filter objects passed from the UI to services for history and log screens.

Layer: models
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class TransactionFilter:
    """Filters for the stock-transaction history.

    Attributes:
        product_id: Only movements of this product.
        tx_type: Only ``IN``, ``OUT`` or ``ADJUST``.
        date_from: Inclusive start date.
        date_to: Inclusive end date.
    """

    product_id: int | None = None
    tx_type: str | None = None
    date_from: date | None = None
    date_to: date | None = None


@dataclass
class ActivityFilter:
    """Filters for the activity-log screen.

    Attributes:
        date_from: Inclusive start date.
        date_to: Inclusive end date.
        action: Only this action.
        entity: Only this entity type.
        user: Only this operator.
    """

    date_from: date | None = None
    date_to: date | None = None
    action: str | None = None
    entity: str | None = None
    user: str | None = None
