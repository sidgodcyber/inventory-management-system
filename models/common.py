"""Shared model helpers: row mapping, list queries and paginated results.

Layer: models (shared data structures, no behaviour beyond derived values)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from typing import Any, Generic, TypeVar

T = TypeVar("T")


def row_to_kwargs(model: type, row: Mapping[str, Any]) -> dict[str, Any]:
    """Pick the keys of ``row`` that match fields of the dataclass ``model``.

    Args:
        model: A dataclass type.
        row: A ``sqlite3.Row`` or dict.

    Returns:
        Keyword arguments suitable for ``model(**kwargs)``.
    """
    keys = set(row.keys())
    return {f.name: row[f.name] for f in fields(model) if f.name in keys}


@dataclass
class ListQuery:
    """Search, sort and pagination options for list screens.

    Attributes:
        search: Free-text filter (matched with ``LIKE``); empty means all rows.
        sort_by: Column key to sort by; repositories whitelist allowed keys.
        descending: Sort direction.
        page: 1-based page number.
        page_size: Rows per page (from the ``page_size`` setting).
    """

    search: str = ""
    sort_by: str = "name"
    descending: bool = False
    page: int = 1
    page_size: int = 15

    @property
    def offset(self) -> int:
        """Row offset for ``LIMIT ... OFFSET``."""
        return max(self.page - 1, 0) * self.page_size


@dataclass
class Page(Generic[T]):
    """One page of results plus the information needed for pager controls.

    Attributes:
        items: Records on this page.
        total: Total number of matching records.
        page: Current 1-based page number.
        page_size: Rows per page.
    """

    items: list[T] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 15

    @property
    def pages(self) -> int:
        """Total number of pages (at least 1, so the pager never shows 0 of 0)."""
        return max(1, math.ceil(self.total / self.page_size)) if self.page_size else 1

    @property
    def has_previous(self) -> bool:
        """True when a previous page exists."""
        return self.page > 1

    @property
    def has_next(self) -> bool:
        """True when a next page exists."""
        return self.page < self.pages
