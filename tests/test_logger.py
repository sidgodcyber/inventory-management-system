"""Tests for :mod:`core.logger` (QO4: full traceability).

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from config.config_loader import AppConfig
from core import logger as core_logger
from core.logger import (
    APP_LOGGER_NAME,
    configure_activity_logger,
    diff_changes,
    get_logger,
    log_activity,
    set_log_level,
    setup_file_logging,
)


class FakeSink:
    """In-memory stand-in for the activity-log repository."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def insert_activity(self, timestamp, user, action, entity, entity_id, details_json, level):
        """Record the call and return a fake id."""
        self.rows.append(
            dict(timestamp=timestamp, user=user, action=action, entity=entity,
                 entity_id=entity_id, details=json.loads(details_json), level=level)
        )
        return len(self.rows)


@pytest.fixture()
def sink() -> FakeSink:
    """Install a fake sink for the duration of one test."""
    fake = FakeSink()
    configure_activity_logger(fake, lambda: "Tester")
    yield fake
    core_logger._activity_logger = None


def test_log_activity_writes_structured_row(sink: FakeSink) -> None:
    """Entries carry user, action, entity, id, details and level."""
    new_id = log_activity("CREATE", "Product", 7, {"new": {"sku": "A1"}})
    row = sink.rows[0]
    assert new_id == 1
    assert row["user"] == "Tester" and row["action"] == "CREATE"
    assert row["entity_id"] == "7" and row["details"] == {"new": {"sku": "A1"}}
    assert row["level"] == "INFO" and len(row["timestamp"]) == 19


def test_explicit_user_overrides_operator(sink: FakeSink) -> None:
    """A caller may record a different user, e.g. the seed script."""
    log_activity("LOGIN", "System", user="Seeder")
    assert sink.rows[0]["user"] == "Seeder"


def test_invalid_action_is_rejected(sink: FakeSink) -> None:
    """Unknown actions are a programming error and raise immediately."""
    with pytest.raises(ValueError, match="action"):
        log_activity("TELEPORT", "Product")


def test_invalid_level_is_rejected(sink: FakeSink) -> None:
    """Unknown levels raise."""
    with pytest.raises(ValueError, match="level"):
        log_activity("CREATE", "Product", level="LOUD")


def test_log_activity_without_sink_returns_none() -> None:
    """Before configuration the helper degrades gracefully."""
    core_logger._activity_logger = None
    assert log_activity("CREATE", "Product") is None


def test_diff_changes_only_reports_changed_fields() -> None:
    """Unchanged fields are omitted from UPDATE payloads."""
    diff = diff_changes({"name": "Pen", "price": 10}, {"name": "Pen", "price": 12})
    assert diff == {"price": {"old": 10, "new": 12}}


def test_setup_file_logging_writes_to_rotating_file(
    tmp_path: Path, config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The file channel writes to the configured path at the configured level."""
    log_file = tmp_path / "logs" / "test.log"
    data = config.as_dict()
    data["paths"]["log_file"] = str(log_file)
    path = setup_file_logging(AppConfig(data, config.source), level="DEBUG")
    get_logger("test").debug("hello file log")
    for handler in logging.getLogger(APP_LOGGER_NAME).handlers:
        handler.flush()
    assert path == log_file
    assert "hello file log" in log_file.read_text(encoding="utf-8")
    _remove_handlers()


def test_set_log_level_changes_level() -> None:
    """The level can change at runtime and invalid names are refused."""
    set_log_level("ERROR")
    assert logging.getLogger(APP_LOGGER_NAME).level == logging.ERROR
    with pytest.raises(ValueError):
        set_log_level("VERBOSE")
    set_log_level("INFO")


def _remove_handlers() -> None:
    """Detach and close handlers so temporary files can be deleted."""
    root = logging.getLogger(APP_LOGGER_NAME)
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
