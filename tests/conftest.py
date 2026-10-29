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


@pytest.fixture()
def config() -> AppConfig:
    """Return the shipped, validated configuration."""
    return load_config()


@pytest.fixture()
def db(tmp_path: Path) -> Iterator[Database]:
    """Yield an initialised database stored in a temporary folder."""
    database = Database(tmp_path / "test.db")
    database.initialize()
    yield database
    database.close()


@pytest.fixture()
def services(config: AppConfig, db: Database) -> Iterator[AppServices]:
    """Fully wired services over the temporary database."""
    yield build_services(config, db)
    core_logger._activity_logger = None


@pytest.fixture()
def audit(db: Database):
    """Return a helper listing activity entries, optionally for one action."""
    repo = ActivityLogRepository(db)

    def entries(action: str | None = None) -> list[ActivityLog]:
        """Activity rows (oldest first), filtered by ``action`` when given."""
        page = repo.find(ActivityFilter(action=action), ListQuery(sort_by="timestamp",
                                                                   page_size=1000))
        return sorted(page.items, key=lambda entry: entry.id)

    return entries
