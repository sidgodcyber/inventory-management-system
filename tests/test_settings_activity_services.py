"""Tests for the settings, activity and system services (Q11 features 3-5).

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from config.config_loader import AppConfig
from core.exceptions import StockError, ValidationError
from core.logger import APP_LOGGER_NAME, log_activity
from models.common import ListQuery
from models.filters import ActivityFilter
from services.container import AppServices


# -- settings -------------------------------------------------------------------
def test_save_logs_settings_change_with_old_and_new(services: AppServices, audit) -> None:
    """Each changed setting gets its own SETTINGS_CHANGE entry."""
    applied = services.settings.save({"page_size": "25", "currency_symbol": "$",
                                      "operator_name": "Admin"})
    entries = audit("SETTINGS_CHANGE")
    assert set(applied) == {"page_size", "currency_symbol"}
    assert {e.entity_id: e.details for e in entries}["page_size"] == {"old": 15, "new": 25}
    assert services.settings.get("page_size") == 25


def test_invalid_setting_saves_nothing(services: AppServices, audit) -> None:
    """One bad value rejects the whole form (all-or-nothing)."""
    with pytest.raises(ValidationError):
        services.settings.save({"currency_symbol": "$", "page_size": "1000"})
    assert services.settings.get("currency_symbol") != "$"
    assert audit("SETTINGS_CHANGE") == []


@pytest.mark.parametrize(
    ("key", "value"),
    [("date_format", "dd-mm-yyyy"), ("log_level", "LOUD"), ("appearance_mode", "neon"),
     ("operator_name", " "), ("log_retention_days", "0"), ("operator_role", "CEO")],
)
def test_setting_rules(services: AppServices, key: str, value: str) -> None:
    """Every setting has a validation rule."""
    with pytest.raises(ValidationError):
        services.settings.save({key: value})


def test_log_level_applies_immediately(services: AppServices) -> None:
    """Changing log level reconfigures the file logger at once (no restart)."""
    services.settings.save({"log_level": "debug"})
    assert logging.getLogger(APP_LOGGER_NAME).level == logging.DEBUG
    services.settings.save({"log_level": "INFO"})


def test_listeners_receive_changes(services: AppServices) -> None:
    """The UI can subscribe to apply theme/page size live."""
    seen: list[tuple[str, object]] = []
    services.settings.subscribe(lambda key, value: seen.append((key, value)))
    services.settings.save({"appearance_mode": "dark"})
    assert ("appearance_mode", "dark") in seen


def test_reset_to_defaults(services: AppServices, config: AppConfig, audit) -> None:
    """Reset restores config.json values and audits each reverted setting."""
    services.settings.save({"page_size": "40", "currency_symbol": "€"})
    reverted = services.settings.reset_to_defaults()
    assert services.settings.get("page_size") == config.get("display.page_size")
    assert set(reverted) == {"page_size", "currency_symbol"}
    assert len(audit("SETTINGS_CHANGE")) == 4


def test_options_and_operator_used_in_audit(services: AppServices, audit) -> None:
    """Choice lists come from config; the operator setting becomes the audit user."""
    assert "Store Staff" in services.settings.options("operator_role")
    assert services.settings.options("page_size") is None
    services.settings.save({"operator_name": "Siddhi"})
    services.categories.create("Toys")
    assert audit("CREATE")[0].user == "Siddhi"


# -- activity -------------------------------------------------------------------
def test_record_expected_error_is_warning(services: AppServices, audit) -> None:
    """User mistakes are stored as ERROR/WARNING with structured details."""
    services.activity.record_error("Stock > Stock out", StockError("only 2 in stock"))
    entry = audit("ERROR")[0]
    assert entry.level == "WARNING" and entry.details["type"] == "StockError"
    assert entry.details["context"] == "Stock > Stock out" and entry.details["expected"]


def test_record_unexpected_error_has_traceback(services: AppServices, audit) -> None:
    """Defects are stored at ERROR level with a short traceback."""
    try:
        {}["missing"]
    except KeyError as exc:
        services.activity.record_error("Dashboard > refresh", exc)
    entry = audit("ERROR")[0]
    assert entry.level == "ERROR" and entry.details["traceback"]


def test_purge_respects_retention(services: AppServices, db, audit) -> None:
    """Only entries older than the retention period are purged; the purge is logged."""
    from repositories.activity_log_repository import ActivityLogRepository

    repo = ActivityLogRepository(db)
    repo.insert_activity("2020-01-01 00:00:00", "Old", "LOGIN", "System", None, "{}", "INFO")
    log_activity("LOGIN", "System")
    assert services.activity.expired_count() == 1
    assert services.activity.purge_expired() == 1
    assert audit("DELETE")[0].details["purged_entries"] == 1
    assert services.activity.find(ActivityFilter(user="Old"), ListQuery()).total == 0


def test_activity_export_and_filters(services: AppServices, tmp_path: Path) -> None:
    """Export writes filtered entries; filter options list known values."""
    services.activity.record_login()
    services.categories.create("Toys")
    path = services.activity.export_csv(ActivityFilter(action="CREATE"), tmp_path / "a.csv")
    frame = pd.read_csv(path, encoding="utf-8-sig")
    assert list(frame["Action"]) == ["CREATE"]
    options = services.activity.filter_options()
    assert "Category" in options["entities"] and "Admin" in options["users"]
    assert dict(services.activity.action_counts())["LOGIN"] == 1


def test_retention_cutoff(services: AppServices) -> None:
    """The cutoff is midnight, retention-days before today."""
    services.settings.save({"log_retention_days": "30"})
    assert services.activity.retention_cutoff(date(2026, 3, 31)) == "2026-03-01 00:00:00"


# -- system ---------------------------------------------------------------------
def test_module_inventory_covers_every_layer(services: AppServices) -> None:
    """The About screen lists modules from each layer with docstring summaries."""
    modules = services.system.modules()
    layers = {m.layer for m in modules}
    assert {"Business", "Data access", "Infrastructure"} <= layers
    assert all(m.summary != "(no docstring)" for m in modules)
    assert services.system.app_info()["Schema version"] == "1"
