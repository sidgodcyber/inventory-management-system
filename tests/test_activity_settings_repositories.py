"""Tests for the activity-log and settings repositories.

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from datetime import date

import pytest

from config.config_loader import AppConfig
from core.database import Database
from core.settings_manager import SettingsManager
from models.common import ListQuery
from models.filters import ActivityFilter
from repositories.activity_log_repository import ActivityLogRepository
from repositories.settings_repository import SettingsRepository


@pytest.fixture()
def activity(db: Database) -> ActivityLogRepository:
    """Activity repository with three entries."""
    repo = ActivityLogRepository(db)
    repo.insert_activity("2026-01-01 08:00:00", "Asha", "CREATE", "Product", "1", "{}", "INFO")
    repo.insert_activity("2026-02-01 08:00:00", "Ravi", "STOCK_OUT", "Product", "1",
                         '{"old": 10, "new": 4}', "INFO")
    repo.insert_activity("2026-03-01 08:00:00", "Asha", "ERROR", "System", None,
                         '{"error": "boom"}', "ERROR")
    return repo


def test_find_filters_and_sorts(activity: ActivityLogRepository) -> None:
    """Action, user and date filters combine; newest first by default sort."""
    assert activity.find(ActivityFilter(user="Asha"), ListQuery()).total == 2
    assert activity.find(ActivityFilter(action="ERROR"), ListQuery()).total == 1
    feb = ActivityFilter(date_from=date(2026, 2, 1), date_to=date(2026, 2, 28))
    assert activity.find(feb, ListQuery()).items[0].action == "STOCK_OUT"
    newest = activity.find(ActivityFilter(), ListQuery(sort_by="timestamp", descending=True))
    assert newest.items[0].action == "ERROR"


def test_search_matches_details(activity: ActivityLogRepository) -> None:
    """Free text searches inside the JSON payload."""
    assert activity.find(ActivityFilter(), ListQuery(search="boom")).total == 1


def test_purge_before_cutoff(activity: ActivityLogRepository) -> None:
    """Only entries strictly older than the cutoff are deleted."""
    assert activity.count_before("2026-02-01 08:00:00") == 1
    assert activity.purge_before("2026-02-01 08:00:00") == 1
    assert activity.count() == 2


def test_distinct_values_whitelisted(activity: ActivityLogRepository) -> None:
    """Filter drop-downs list distinct users; other columns are refused."""
    assert activity.distinct_values("user") == ["Asha", "Ravi"]
    with pytest.raises(ValueError):
        activity.distinct_values("details_json")


def test_count_by_action_and_export_order(activity: ActivityLogRepository) -> None:
    """Pareto counts and export ordering."""
    assert dict(activity.count_by_action()) == {"CREATE": 1, "STOCK_OUT": 1, "ERROR": 1}
    assert activity.list_filtered(ActivityFilter())[0].action == "ERROR"


def test_settings_upsert_and_list(db: Database) -> None:
    """Values upsert by key."""
    repo = SettingsRepository(db)
    repo.set_value("page_size", "15", "int", "Rows")
    repo.set_value("page_size", "20", "int", "Rows")
    assert repo.get_value("page_size") == "20"
    assert repo.get_value("missing") is None
    assert [s.key for s in repo.list_all()] == ["page_size"]


def test_settings_manager_over_real_repository(db: Database, config: AppConfig) -> None:
    """The repository satisfies the SettingsStore protocol end-to-end."""
    manager = SettingsManager(SettingsRepository(db), config)
    manager.seed_defaults()
    manager.set("currency_symbol", "$")
    assert SettingsManager(SettingsRepository(db), config).get("currency_symbol") == "$"
