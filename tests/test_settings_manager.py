"""Tests for :mod:`core.settings_manager` (QO3: behaviour changeable at runtime).

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import pytest

from config.config_loader import AppConfig
from core.exceptions import ValidationError
from core.settings_manager import SETTING_DEFINITIONS, SettingsManager, coerce, serialize


class MemoryStore:
    """Dictionary-backed :class:`SettingsStore` used to test the manager alone."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def get_value(self, key: str) -> str | None:
        """Return the raw value."""
        return self.data.get(key)

    def set_value(self, key: str, value: str, value_type: str, description: str) -> None:
        """Store the raw value."""
        self.data[key] = value

    def all_values(self) -> dict[str, str]:
        """Return a copy of all values."""
        return dict(self.data)


@pytest.fixture()
def store() -> MemoryStore:
    """Fresh empty store."""
    return MemoryStore()


@pytest.fixture()
def manager(store: MemoryStore, config: AppConfig) -> SettingsManager:
    """Manager over the empty store, seeded from config."""
    settings = SettingsManager(store, config)
    settings.seed_defaults()
    return settings


def test_seed_copies_every_default(store: MemoryStore, config: AppConfig) -> None:
    """First run inserts one row per definition; second run inserts none."""
    settings = SettingsManager(store, config)
    assert len(settings.seed_defaults()) == len(SETTING_DEFINITIONS)
    assert settings.seed_defaults() == []
    assert store.data["page_size"] == str(config.get("display.page_size"))


def test_get_returns_typed_values(manager: SettingsManager, config: AppConfig) -> None:
    """Integers come back as int, not text."""
    assert manager.get("page_size") == config.get("display.page_size")
    assert isinstance(manager.get("default_reorder_level"), int)


def test_set_persists_and_returns_old_new(manager: SettingsManager, store: MemoryStore) -> None:
    """Changing a value updates the store and reports old -> new."""
    old, new = manager.set("page_size", "25")
    assert (new, store.data["page_size"]) == (25, "25")
    assert old != new


def test_set_bad_type_raises(manager: SettingsManager) -> None:
    """Non-numeric text for an int setting is a validation error."""
    with pytest.raises(ValidationError, match="Rows per page"):
        manager.set("page_size", "many")


def test_listeners_notified_only_on_change(manager: SettingsManager) -> None:
    """Listeners fire once per real change."""
    calls: list[tuple] = []
    manager.subscribe(lambda key, value: calls.append((key, value)))
    manager.set("currency_symbol", "$")
    manager.set("currency_symbol", "$")
    assert calls == [("currency_symbol", "$")]


def test_unsubscribed_listener_not_called(manager: SettingsManager) -> None:
    """Closed windows stop receiving notifications."""
    calls: list[str] = []
    listener = lambda key, value: calls.append(key)  # noqa: E731
    manager.subscribe(listener)
    manager.unsubscribe(listener)
    manager.set("currency_symbol", "$")
    assert calls == []


def test_missing_row_falls_back_to_config(store: MemoryStore, config: AppConfig) -> None:
    """With nothing stored, defaults come from config.json."""
    settings = SettingsManager(store, config)
    assert settings.get("currency_symbol") == config.get("inventory.currency_symbol")


def test_corrupt_row_falls_back_to_config(store: MemoryStore, config: AppConfig) -> None:
    """Garbage in the table never crashes the app."""
    store.data["page_size"] = "not-a-number"
    assert SettingsManager(store, config).get("page_size") == config.get("display.page_size")


def test_unknown_key_raises(manager: SettingsManager) -> None:
    """Typos in setting names are caught."""
    with pytest.raises(KeyError):
        manager.get("pagesize")


def test_coerce_and_serialize_round_trip() -> None:
    """Booleans and numbers survive the text round-trip."""
    assert coerce(serialize(True), "bool") is True
    assert coerce(serialize(False), "bool") is False
    assert coerce(" 3.5 ", "float") == 3.5
