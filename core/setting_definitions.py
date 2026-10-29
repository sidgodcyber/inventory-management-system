"""Catalogue of runtime settings and their text <-> value conversion.

Each :class:`SettingDefinition` maps a runtime setting to the ``config.json``
key that supplies its default. Adding a new runtime setting is a one-line
change here; the Settings screen and validation pick it up automatically.

Layer: core
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from core.exceptions import ValidationError


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
