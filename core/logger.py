"""Two-channel logging: a rotating technical log file and a business audit trail.

Channel 1, the **file log**: standard :mod:`logging` with a
:class:`~logging.handlers.RotatingFileHandler` writing to ``logs/app.log``. Its
level comes from the runtime ``log_level`` setting and can change at runtime
through :func:`set_log_level`.

Channel 2, the **activity log**: structured rows in the ``activity_log`` table.
Services record every create/update/delete, stock movement, settings change,
export and error through the single helper :func:`log_activity`. The helper
does not write SQL itself. It forwards to an injected :class:`ActivitySink`
(implemented by ``ActivityLogRepository``), so core never imports upward.

Layer: core (usable by every layer)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Protocol

from config.config_loader import AppConfig
from core.constants import ACTIONS, DB_TIMESTAMP_FORMAT, LOG_LEVELS

APP_LOGGER_NAME = "ims"


class ActivitySink(Protocol):
    """Anything that can persist one audit-trail row (the repository)."""

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
        """Store one activity row and return its id."""
        ...


# -- channel 1: file logging ---------------------------------------------------
def get_logger(name: str) -> logging.Logger:
    """Return a child of the application logger, e.g. ``ims.services.stock``.

    Args:
        name: Usually the caller's ``__name__``.

    Returns:
        A :class:`logging.Logger` that writes to ``logs/app.log`` once configured.
    """
    return logging.getLogger(f"{APP_LOGGER_NAME}.{name}")


def setup_file_logging(config: AppConfig, level: str | None = None) -> Path:
    """Attach a rotating file handler to the application logger.

    Calling it again replaces the previous handler, so it is safe to re-run.

    Args:
        config: Source of the log path, format, rotation size and backup count.
        level: Optional level overriding ``logging.level`` from config.

    Returns:
        The absolute path of the log file.
    """
    log_path = config.resolve_path("paths.log_file")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger(APP_LOGGER_NAME)
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    handler = RotatingFileHandler(
        log_path,
        maxBytes=config.get("logging.max_bytes"),
        backupCount=config.get("logging.backup_count"),
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(config.get("logging.format")))
    root.addHandler(handler)
    set_log_level(level or config.get("logging.level"))
    return log_path


def set_log_level(level: str) -> None:
    """Change the file-log level at runtime.

    Args:
        level: One of :data:`core.constants.LOG_LEVELS`.

    Raises:
        ValueError: If the level name is unknown.
    """
    if level not in LOG_LEVELS:
        raise ValueError(f"Unknown log level '{level}'")
    logging.getLogger(APP_LOGGER_NAME).setLevel(level)


# -- channel 2: business activity log ---------------------------------------------
class ActivityLogger:
    """Writes audit rows to a sink and mirrors them into the file log.

    Args:
        sink: Persists rows (the activity-log repository).
        user_provider: Returns the current operator name (from settings).
    """

    def __init__(self, sink: ActivitySink, user_provider: Callable[[], str]) -> None:
        self._sink = sink
        self._user_provider = user_provider
        self._file_log = get_logger("activity")

    def log(
        self,
        action: str,
        entity: str,
        entity_id: Any = None,
        details: Mapping[str, Any] | None = None,
        level: str = "INFO",
        user: str | None = None,
    ) -> int:
        """Validate and store one activity entry.

        Args:
            action: One of :data:`core.constants.ACTIONS`.
            entity: Entity name, e.g. ``"Product"``.
            entity_id: Primary key (or setting key) of the affected record.
            details: JSON-serialisable payload, typically old/new values.
            level: Logging level name for this entry.
            user: Operator name; defaults to the current operator setting.

        Returns:
            The id of the inserted activity row.

        Raises:
            ValueError: If ``action`` or ``level`` is not recognised.
        """
        _check_choice("action", action, ACTIONS)
        _check_choice("level", level, LOG_LEVELS)
        operator = user or self._user_provider()
        details_json = json.dumps(dict(details or {}), default=str, ensure_ascii=False)
        ref = None if entity_id is None else str(entity_id)
        self._file_log.log(
            logging.getLevelName(level),
            "%s %s#%s by %s %s", action, entity, ref, operator, details_json,
        )
        timestamp = datetime.now().strftime(DB_TIMESTAMP_FORMAT)
        return self._sink.insert_activity(
            timestamp, operator, action, entity, ref, details_json, level
        )


def _check_choice(name: str, value: str, allowed: tuple[str, ...]) -> None:
    """Raise ``ValueError`` when ``value`` is not in ``allowed``."""
    if value not in allowed:
        raise ValueError(f"Invalid activity {name} '{value}'")


_activity_logger: ActivityLogger | None = None


def configure_activity_logger(
    sink: ActivitySink, user_provider: Callable[[], str]
) -> ActivityLogger:
    """Install the process-wide activity logger used by :func:`log_activity`.

    Args:
        sink: Persists rows (the activity-log repository).
        user_provider: Returns the current operator name.

    Returns:
        The newly installed :class:`ActivityLogger`.
    """
    global _activity_logger
    _activity_logger = ActivityLogger(sink, user_provider)
    return _activity_logger


def log_activity(
    action: str,
    entity: str,
    entity_id: Any = None,
    details: Mapping[str, Any] | None = None,
    *,
    level: str = "INFO",
    user: str | None = None,
) -> int | None:
    """Record a business event: the **only** way services write the audit trail.

    Args:
        action: One of :data:`core.constants.ACTIONS`.
        entity: Entity name, e.g. ``"Product"``.
        entity_id: Primary key (or key) of the affected record.
        details: JSON-serialisable payload, typically old/new values.
        level: Logging level name for this entry.
        user: Operator override; defaults to the current operator setting.

    Returns:
        The new activity id, or ``None`` if no sink is configured yet (the
        event is still written to the file log).
    """
    if _activity_logger is None:
        get_logger("activity").warning("Activity logger not configured: %s %s", action, entity)
        return None
    return _activity_logger.log(action, entity, entity_id, details, level, user)


def diff_changes(old: Mapping[str, Any], new: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Build the ``{"field": {"old": x, "new": y}}`` payload for UPDATE entries.

    Args:
        old: Field values before the change.
        new: Field values after the change.

    Returns:
        Only the fields whose value actually changed.
    """
    return {
        key: {"old": old.get(key), "new": value}
        for key, value in new.items()
        if old.get(key) != value
    }
