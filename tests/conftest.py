"""Shared pytest fixtures: a fresh, migrated database for every test.

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from config.config_loader import AppConfig, load_config
from core import logger as core_logger
from core.database import Database
from models.activity_log import ActivityLog
from models.common import ListQuery
from models.filters import ActivityFilter
from repositories.activity_log_repository import ActivityLogRepository
from services.container import AppServices, build_services


#: PBKDF2 work factor for tests (the shipped value is deliberately slow).
TEST_PBKDF2_ITERATIONS = 1_000


@pytest.fixture()
def config() -> AppConfig:
    """Return the shipped configuration with a fast password work factor."""
    shipped = load_config()
    data = shipped.as_dict()
    data["auth"]["pbkdf2_iterations"] = TEST_PBKDF2_ITERATIONS
    return AppConfig(data, shipped.source)


@pytest.fixture()
def db(tmp_path: Path) -> Iterator[Database]:
    """Yield an initialised database stored in a temporary folder."""
    database = Database(tmp_path / "test.db")
    database.initialize()
    yield database
    database.close()


@pytest.fixture()
def services(config: AppConfig, db: Database) -> Iterator[AppServices]:
    """Fully wired services, signed in as the initial admin account."""
    wired = build_services(config, db)
    wired.auth.login(config.get("auth.initial_admin_username"),
                     config.get("auth.initial_admin_password"))
    yield wired
    core_logger._activity_logger = None


@pytest.fixture()
def audit(db: Database):
    """Return a helper listing activity entries, optionally for one action."""
    repo = ActivityLogRepository(db)

    def entries(action: str | None = None) -> list[ActivityLog]:
        """Business activity rows (oldest first), filtered by ``action`` when given.

        Account entries (the bootstrap admin and sign-ins) are left out so tests
        can assert on the business events they trigger.
        """
        page = repo.find(ActivityFilter(action=action), ListQuery(sort_by="timestamp",
                                                                   page_size=1000))
        entries = [entry for entry in page.items if entry.entity != "User"]
        return sorted(entries, key=lambda entry: entry.id)

    return entries
