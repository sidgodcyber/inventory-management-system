"""Runtime settings stored in the ``settings`` table, with config.json fallback.

Each runtime setting is declared once in :data:`SETTING_DEFINITIONS`, which maps
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
from dataclasses import dataclass
from typing import Any, Protocol

from config.config_loader import AppConfig
from core.exceptions import ValidationError

SettingListener = Callable[[str, Any], None]


@dataclass(frozen=True)
class SettingDefinition:
    """Metadata describing one runtime setting.

    Attributes:
        key: Name used in the ``settings`` table.
        config_key: Dotted ``config.json`` key holding the default value.
        value_type: One of ``str``, ``int``, ``float``, ``bool``.
        label: Short label shown on the Settings screen.
        description: Longer help text stored alongside the value.
    """

    key: str
    config_key: str
    value_type: str
    label: str
    description: str


SETTING_DEFINITIONS: tuple[SettingDefinition, ...] = (
    SettingDefinition("appearance_mode", "ui.appearance_mode", "str",
                      "Appearance mode", "Light, dark, or follow the operating system"),
    SettingDefinition("currency_symbol", "inventory.currency_symbol", "str",
                      "Currency symbol", "Prefix used when displaying money"),
    SettingDefinition("default_reorder_level", "inventory.default_reorder_level", "int",
                      "Default reorder level", "Low-stock threshold pre-filled for new products"),
    SettingDefinition("page_size", "display.page_size", "int",
                      "Rows per page", "Number of rows shown in every paginated table"),
    SettingDefinition("date_format", "display.date_format", "str",
                      "Date format", "strftime pattern for displaying and typing dates"),
    SettingDefinition("log_level", "logging.level", "str",
                      "Log level", "Minimum level written to logs/app.log"),
    SettingDefinition("log_retention_days", "activity_log.retention_days", "int",
                      "Activity-log retention (days)", "Entries older than this can be purged"),
    SettingDefinition("operator_name", "operator.name", "str",
                      "Operator name", "Recorded as the user on every activity-log entry"),
    SettingDefinition("operator_role", "operator.role", "str",
                      "Operator role", "Admin / Store Manager / Store Staff"),
)


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


def serialize(value: Any) -> str:
    """Convert a typed value to the text stored in the ``settings`` table."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def coerce(raw: Any, value_type: str, label: str = "Value") -> Any:
    """Convert raw text (or a typed value) to ``value_type``.

    Args:
        raw: Stored text or a value typed by the user.
        value_type: Target type name.
        label: Field name used in the error message.

    Returns:
        The converted value.

    Raises:
        ValidationError: If the value cannot be converted.
    """
    converters: dict[str, Callable[[Any], Any]] = {
        "str": lambda v: str(v).strip(),
        "int": lambda v: int(str(v).strip()),
        "float": lambda v: float(str(v).strip()),
        "bool": lambda v: str(v).strip().lower() in ("1", "true", "yes", "on"),
    }
    try:
        return converters[value_type](raw)
    except (KeyError, ValueError) as exc:
        raise ValidationError(f"{label} must be a valid {value_type}.") from exc


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
