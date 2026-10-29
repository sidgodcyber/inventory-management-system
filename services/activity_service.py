"""Activity-log screen support plus central error recording.

:meth:`ActivityService.record_error` is called by the UI's single error
handler for every caught exception. Expected errors (:class:`AppError`, e.g.
a validation failure or an attempted over-issue) are stored at ``WARNING``
level. Unexpected defects are stored at ``ERROR`` level with a short
traceback. Both use action ``ERROR`` with a structured payload (context,
type, message), which is what the defect checksheet and Pareto chart of later
TQM reviews are built from.

Layer: services
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import traceback
from datetime import date, datetime
from pathlib import Path

from config.config_loader import AppConfig
from core.constants import (
    ACTION_DELETE,
    ACTION_ERROR,
    ACTION_EXPORT,
    ACTION_LOGIN,
    ACTIONS,
    ENTITY_ACTIVITY_LOG,
    ENTITY_SYSTEM,
)
from core.database import Database
from core.exceptions import AppError
from core.logger import get_logger, log_activity
from core.settings_manager import SettingsManager
from models.activity_log import ActivityLog
from models.common import ListQuery, Page
from models.filters import ActivityFilter
from repositories.activity_log_repository import ActivityLogRepository
from utils.csv_export import default_export_path, write_csv
from utils.date_helpers import days_ago, start_of_day

EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("timestamp", "Timestamp"),
    ("user", "User"),
    ("action", "Action"),
    ("entity", "Entity"),
    ("entity_id", "Entity ID"),
    ("level", "Level"),
    ("details_json", "Details"),
)

# Number of traceback lines kept for unexpected errors (enough to locate the defect).
_TRACEBACK_LINES = 6

_log = get_logger(__name__)


class ActivityService:
    """Query, export and purge the audit trail; record errors and logins.

    Args:
        repo: Activity-log repository.
        settings: Runtime settings (retention days, operator role).
        db: Database, used only to open atomic transactions.
        config: Configuration (export folder, app version).
    """

    def __init__(self, repo: ActivityLogRepository, settings: SettingsManager, db: Database,
                 config: AppConfig) -> None:
        self._repo = repo
        self._settings = settings
        self._db = db
        self._config = config

    # -- queries ------------------------------------------------------------------
    def find(self, filters: ActivityFilter, query: ListQuery) -> Page[ActivityLog]:
        """One page of filtered entries."""
        return self._repo.find(filters, query)

    def filter_options(self) -> dict[str, list[str]]:
        """Values for the action, entity and user filter drop-downs."""
        return {
            "actions": list(ACTIONS),
            "entities": self._repo.distinct_values("entity"),
            "users": self._repo.distinct_values("user"),
        }

    def action_counts(self) -> list[tuple[str, int]]:
        """Entries per action, largest first (input for a Pareto chart)."""
        return self._repo.count_by_action()

    # -- retention ----------------------------------------------------------------
    def retention_days(self) -> int:
        """Current retention setting in days."""
        return int(self._settings.get("log_retention_days"))

    def retention_cutoff(self, today: date | None = None) -> str:
        """Timestamp before which entries are past retention."""
        return start_of_day(days_ago(self.retention_days(), today))

    def expired_count(self, today: date | None = None) -> int:
        """How many entries a purge would remove (shown in the confirmation)."""
        return self._repo.count_before(self.retention_cutoff(today))

    def purge_expired(self, today: date | None = None) -> int:
        """Delete entries older than the retention period and log the purge.

        Returns:
            Number of deleted entries.
        """
        cutoff = self.retention_cutoff(today)
        with self._db.transaction():
            removed = self._repo.purge_before(cutoff)
            log_activity(ACTION_DELETE, ENTITY_ACTIVITY_LOG, None, {
                "purged_entries": removed, "cutoff": cutoff,
                "retention_days": self.retention_days(),
            })
        return removed

    # -- export -------------------------------------------------------------------
    def export_csv(self, filters: ActivityFilter, path: Path | None = None) -> Path:
        """Export filtered entries to CSV and log ``EXPORT``."""
        rows = [entry.to_dict() for entry in self._repo.list_filtered(filters)]
        target = path or default_export_path(self._config.resolve_path("paths.export_dir"),
                                             "activity_log")
        write_csv(rows, EXPORT_COLUMNS, target)
        log_activity(ACTION_EXPORT, ENTITY_ACTIVITY_LOG, None,
                     {"file": str(target), "rows": len(rows)})
        return target

    # -- events -------------------------------------------------------------------
    def record_login(self) -> None:
        """Log the start of a session (single-login app: operator from settings)."""
        log_activity(ACTION_LOGIN, ENTITY_SYSTEM, None, {
            "role": self._settings.get("operator_role"),
            "version": self._config.get("app.version"),
            "started_at": datetime.now().isoformat(timespec="seconds"),
        })

    def record_error(self, context: str, error: BaseException,
                     entity: str = ENTITY_SYSTEM) -> None:
        """Store a caught exception as an ``ERROR`` entry. Never raises.

        Args:
            context: Where it happened, e.g. ``"Stock > Stock out"``.
            error: The caught exception.
            entity: Entity the operation concerned.
        """
        expected = isinstance(error, AppError)
        details = {"context": context, "type": type(error).__name__,
                   "message": getattr(error, "message", str(error)), "expected": expected}
        if not expected:
            details["traceback"] = _short_traceback(error)
            _log.error("Unexpected error in %s", context, exc_info=error)
        try:
            log_activity(ACTION_ERROR, entity, None, details,
                         level="WARNING" if expected else "ERROR")
        except Exception:  # noqa: BLE001 - the error handler itself must never crash the UI
            _log.exception("Could not write ERROR activity entry for %s", context)


def _short_traceback(error: BaseException) -> list[str]:
    """Last few formatted traceback lines of ``error``."""
    lines = traceback.format_exception(type(error), error, error.__traceback__)
    return [line.rstrip() for line in lines[-_TRACEBACK_LINES:]]
