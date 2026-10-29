"""Base repository: shared pagination, sorting and filtering helpers.

Sorting is driven by a per-repository whitelist (:attr:`BaseRepository.SORT_COLUMNS`)
that maps UI column keys to SQL expressions. User input therefore never
reaches an ``ORDER BY`` clause directly, which rules out SQL injection.

Layer: repositories (talks to core/database)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date
from typing import Any, TypeVar

from core.database import Database
from models.common import ListQuery, Page
from utils.date_helpers import end_of_day, now_timestamp, start_of_day

T = TypeVar("T")


class BaseRepository:
    """Common plumbing for entity repositories.

    Args:
        db: The shared :class:`~core.database.Database`.
    """

    #: UI sort key -> SQL expression. Subclasses override.
    SORT_COLUMNS: dict[str, str] = {}
    #: Sort key used when the requested one is not whitelisted.
    DEFAULT_SORT: str = "name"

    def __init__(self, db: Database) -> None:
        self.db = db

    @staticmethod
    def now() -> str:
        """Current local time in database timestamp format."""
        return now_timestamp()

    @staticmethod
    def like(text: str) -> str:
        """Wrap search text for a ``LIKE`` comparison."""
        return f"%{text.strip()}%"

    @staticmethod
    def where(clauses: Sequence[str]) -> str:
        """Join conditions into a ``WHERE`` clause (empty string if none)."""
        return f" WHERE {' AND '.join(clauses)}" if clauses else ""

    @staticmethod
    def day_start(day: date) -> str:
        """Timestamp for the first second of ``day``."""
        return start_of_day(day)

    @staticmethod
    def day_end(day: date) -> str:
        """Timestamp for the last second of ``day``."""
        return end_of_day(day)

    def order_by(self, query: ListQuery) -> str:
        """Build a safe ``ORDER BY`` clause from the whitelist."""
        column = self.SORT_COLUMNS.get(query.sort_by, self.SORT_COLUMNS[self.DEFAULT_SORT])
        direction = "DESC" if query.descending else "ASC"
        return f" ORDER BY {column} {direction}"

    def paginate(
        self,
        select_sql: str,
        count_sql: str,
        params: list[Any],
        query: ListQuery,
        mapper: Callable[[Any], T],
    ) -> Page[T]:
        """Run a count query and one page of a select query.

        Args:
            select_sql: SELECT including joins and WHERE, without ORDER/LIMIT.
            count_sql: Matching ``SELECT COUNT(*)`` with the same WHERE.
            params: Parameters shared by both statements.
            query: Sort and pagination options.
            mapper: Converts a row into a model instance.

        Returns:
            The requested :class:`~models.common.Page`.
        """
        total = int(self.db.query_value(count_sql, params, default=0))
        page_size = max(query.page_size, 1)
        last_page = max(1, -(-total // page_size))  # ceiling division
        page = min(max(query.page, 1), last_page)
        offset = (page - 1) * page_size
        sql = f"{select_sql}{self.order_by(query)} LIMIT ? OFFSET ?"
        rows = self.db.query_all(sql, [*params, page_size, offset])
        return Page([mapper(row) for row in rows], total, page, page_size)
