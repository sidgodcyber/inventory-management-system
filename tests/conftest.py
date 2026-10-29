"""Shared pytest fixtures: a fresh, migrated database for every test.

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from config.config_loader import AppConfig, load_config
from core.database import Database


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
