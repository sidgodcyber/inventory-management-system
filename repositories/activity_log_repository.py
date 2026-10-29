"""Data access for the ``activity_log`` audit trail.

Implements :class:`core.logger.ActivitySink`, so it is the sink that
``log_activity`` writes to. It also provides the filtered queries, CSV export
rows, retention purge and per-action counts that feed the defect checksheet and
Pareto analysis in later TQM reviews.

Layer: repositories
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

from models.activity_log import ActivityLog
from models.common import ListQuery, Page
from models.filters import ActivityFilter
from repositories.base import BaseRepository

# Columns whose distinct values may be listed for filter drop-downs.
_DISTINCT_COLUMNS: frozenset[str] = frozenset({"user", "entity", "action"})


class ActivityLogRepository(BaseRepository):
    """Insert, query and purge audit-trail entries."""

    SORT_COLUMNS = {
        "timestamp": "a.timestamp",
        "user": "a.user",
        "action": "a.action",
        "entity": "a.entity",
        "entity_id": "a.entity_id",
        "level": "a.level",
    }
    DEFAULT_SORT = "timestamp"

    def insert_activity(
        self,
        timestamp: str,
        user: str,
        action: str,
        entity: str,
        entity_id: str | None,
        details_json: str,
        level: str,
    ) -> int:
        """Store one entry (the :class:`~core.logger.ActivitySink` contract).

        Returns:
            The new entry id.
        """
        cursor = self.db.execute(
            "INSERT INTO activity_log "
            "(timestamp, user, action, entity, entity_id, details_json, level) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (timestamp, user, action, entity, entity_id, details_json, level),
        )
        return int(cursor.lastrowid)

    def find(self, filters: ActivityFilter, query: ListQuery) -> Page[ActivityLog]:
        """Filter, sort and paginate entries (search matches the details JSON)."""
        clauses, params = self._filters(filters, query.search)
        where = self.where(clauses)
        return self.paginate(
            f"SELECT a.* FROM activity_log a{where}",
            f"SELECT COUNT(*) FROM activity_log a{where}",
            params, query, ActivityLog.from_row,
        )

    def list_filtered(self, filters: ActivityFilter) -> list[ActivityLog]:
        """Every entry matching ``filters``, newest first (for CSV export)."""
        clauses, params = self._filters(filters, "")
        rows = self.db.query_all(
            f"SELECT a.* FROM activity_log a{self.where(clauses)} "
            "ORDER BY a.timestamp DESC, a.id DESC",
            params,
        )
        return [ActivityLog.from_row(row) for row in rows]

    def _filters(self, filters: ActivityFilter, search: str) -> tuple[list[str], list[Any]]:
        """Translate an :class:`ActivityFilter` into WHERE clauses."""
        conditions: list[tuple[Any, str, Any]] = [
            (filters.date_from, "a.timestamp >= ?",
             filters.date_from and self.day_start(filters.date_from)),
            (filters.date_to, "a.timestamp <= ?",
             filters.date_to and self.day_end(filters.date_to)),
            (filters.action, "a.action = ?", filters.action),
            (filters.entity, "a.entity = ?", filters.entity),
            (filters.user, "a.user = ?", filters.user),
        ]
        clauses = [sql for active, sql, _ in conditions if active]
        params = [value for active, _, value in conditions if active]
        if search.strip():
            clauses.append("(a.details_json LIKE ? OR a.entity_id LIKE ?)")
            params += [self.like(search)] * 2
        return clauses, params

    def purge_before(self, cutoff: str) -> int:
        """Delete entries older than ``cutoff``.

        Args:
            cutoff: DB timestamp; strictly older entries are removed.

        Returns:
            Number of deleted rows.
        """
        return int(self.db.execute("DELETE FROM activity_log WHERE timestamp < ?", (cutoff,)).rowcount)

    def count_before(self, cutoff: str) -> int:
        """Number of entries a purge with ``cutoff`` would delete."""
        return int(
            self.db.query_value(
                "SELECT COUNT(*) FROM activity_log WHERE timestamp < ?", (cutoff,), 0
            )
        )

    def distinct_values(self, column: str) -> list[str]:
        """Sorted distinct values of ``user``, ``entity`` or ``action``.

        Raises:
            ValueError: If ``column`` is not whitelisted.
        """
        if column not in _DISTINCT_COLUMNS:
            raise ValueError(f"Column '{column}' cannot be listed")
        rows = self.db.query_all(
            f"SELECT DISTINCT {column} AS value FROM activity_log "
            f"WHERE {column} <> '' ORDER BY {column}"
        )
        return [row["value"] for row in rows]

    def count_by_action(self) -> list[tuple[str, int]]:
        """Entry counts per action, largest first (Pareto input)."""
        rows = self.db.query_all(
            "SELECT action, COUNT(*) AS n FROM activity_log GROUP BY action ORDER BY n DESC"
        )
        return [(row["action"], int(row["n"])) for row in rows]

    def count(self) -> int:
        """Total number of entries."""
        return int(self.db.query_value("SELECT COUNT(*) FROM activity_log", default=0))
