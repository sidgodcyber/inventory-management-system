"""Table vocabulary shared by views: column definitions, row type and status tags.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

# Row tags understood by every table, mapped to palette colours in apply_tag_colors().
TAG_LOW = "low"
TAG_STOCKOUT = "stockout"
TAG_INACTIVE = "inactive"
TAG_ERROR = "error"
TAG_WARNING = "warning"
TAG_SUCCESS = "success"

Row = tuple[str, Sequence[Any], tuple[str, ...]]  # (row id, values, tags)


@dataclass(frozen=True)
class Column:
    """Definition of one table column.

    Attributes:
        key: Field key; also the sort key passed to services.
        heading: Header text.
        width: Initial width in pixels.
        anchor: ``w`` (left), ``e`` (right) or ``center``.
        sortable: Whether clicking the header sorts by this column.
    """

    key: str
    heading: str
    width: int = 120
    anchor: str = "w"
    sortable: bool = True
