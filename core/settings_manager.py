"""Runtime settings stored in the ``settings`` table, with config.json fallback.

Each runtime setting is declared once in
:data:`core.setting_definitions.SETTING_DEFINITIONS`, which maps
it to the ``config.json`` key that supplies its default. On first run
:meth:`SettingsManager.seed_defaults` copies those defaults into the table.
After that, the table wins, so behaviour changes without editing code or the
config file. A missing or corrupt row falls back to the config default.

Persistence goes through an injected :class:`SettingsStore` (implemented by
``SettingsRepository``), which keeps SQL out of the core layer.

Layer: core (used by services; listeners let the UI react to changes)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from config.config_loader import AppConfig
from core.exceptions import ValidationError
from core.setting_definitions import SETTING_DEFINITIONS, SettingDefinition, coerce, serialize

__all__ = ["SETTING_DEFINITIONS", "SettingDefinition", "SettingListener", "SettingsManager",
           "SettingsStore", "coerce", "serialize"]

SettingListener = Callable[[str, Any], None]


class SettingsStore(Protocol):
    """Persistence contract for settings (implemented by the repository)."""

    def get_value(self, key: str) -> str | None:
        """Return the raw stored value or ``None``."""
        ...

    def set_value(self, key: str, value: str, value_type: str, description: str) -> None:
        """Insert or replace one setting."""
        ...

    def all_values(self) -> dict[str, str]:
        """Return every stored key and raw value."""
        ...


class SettingsManager:
    """Typed access to runtime settings with change notification.

    Args:
        store: Persistence back-end (``SettingsRepository``).
        config: Source of default values.
    """

    def __init__(self, store: SettingsStore, config: AppConfig) -> None:
        self._store = store
        self._config = config
        self._definitions = {d.key: d for d in SETTING_DEFINITIONS}
        self._cache: dict[str, Any] | None = None
        self._listeners: list[SettingListener] = []

    @property
    def definitions(self) -> tuple[SettingDefinition, ...]:
        """All known setting definitions, in display order."""
        return SETTING_DEFINITIONS

    def definition(self, key: str) -> SettingDefinition:
        """Return the definition for ``key``.

        Raises:
            KeyError: If the setting is unknown.
        """
        if key not in self._definitions:
            raise KeyError(f"Unknown setting '{key}'")
        return self._definitions[key]

    def default(self, key: str) -> Any:
        """Return the config.json default for ``key``."""
        return self._config.get(self.definition(key).config_key)

    def seed_defaults(self) -> list[str]:
        """Insert config defaults for any setting missing from the table.

        Returns:
            Keys that were inserted (empty on every run after the first).
        """
        existing = self._store.all_values()
        missing = [d for d in SETTING_DEFINITIONS if d.key not in existing]
        for definition in missing:
            self._write(definition, self.default(definition.key))
        self._cache = None
        return [d.key for d in missing]

    def get(self, key: str) -> Any:
        """Return the typed current value, falling back to the config default."""
        self.definition(key)
        return self._values()[key]

    def get_all(self) -> dict[str, Any]:
        """Return every setting as ``{key: typed value}``."""
        return dict(self._values())

    def set(self, key: str, value: Any) -> tuple[Any, Any]:
        """Persist a new value and notify listeners when it changed.

        Args:
            key: Setting key.
            value: New value (converted to the declared type).

        Returns:
            ``(old_value, new_value)`` as typed values.

        Raises:
            ValidationError: If the value cannot be converted.
        """
        definition = self.definition(key)
        new_value = coerce(value, definition.value_type, definition.label)
        old_value = self.get(key)
        if new_value != old_value:
            self._write(definition, new_value)
            self._values()[key] = new_value
            self._notify(key, new_value)
        return old_value, new_value

    def reload(self) -> None:
        """Drop the in-memory cache so the next read comes from the store."""
        self._cache = None

    def subscribe(self, listener: SettingListener) -> None:
        """Register ``listener(key, new_value)`` to run after every change."""
        self._listeners.append(listener)

    def unsubscribe(self, listener: SettingListener) -> None:
        """Stop notifying ``listener`` (e.g. when the main window closes)."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    # -- internals -------------------------------------------------------------
    def _values(self) -> dict[str, Any]:
        """Load (once) and return the typed cache of all settings."""
        if self._cache is None:
            raw = self._store.all_values()
            self._cache = {d.key: self._typed(d, raw.get(d.key)) for d in SETTING_DEFINITIONS}
        return self._cache

    def _typed(self, definition: SettingDefinition, raw: str | None) -> Any:
        """Convert a stored value, using the default if it is missing or corrupt."""
        if raw is None:
            return self.default(definition.key)
        try:
            return coerce(raw, definition.value_type, definition.label)
        except ValidationError:
            return self.default(definition.key)

    def _write(self, definition: SettingDefinition, value: Any) -> None:
        """Serialise and store one value."""
        self._store.set_value(
            definition.key, serialize(value), definition.value_type, definition.description
        )

    def _notify(self, key: str, value: Any) -> None:
        """Call every registered listener."""
        for listener in self._listeners:
            listener(key, value)
