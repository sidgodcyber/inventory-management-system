"""Single access point for application configuration (``config/config.json``).

The loader reads the JSON file once, validates every required key and its type,
and exposes the values through :class:`AppConfig`. A broken or incomplete file
fails fast with a :class:`ConfigError` listing *every* problem, so the user can
fix the file in one go instead of discovering issues one crash at a time.

Layer: config (usable by every layer)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from core.constants import APPEARANCE_MODES, COLOR_THEMES, LOG_LEVELS

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH: Path = PROJECT_ROOT / "config" / "config.json"

# Every required key (dotted path) and the Python type(s) its value must have.
SCHEMA: dict[str, type | tuple[type, ...]] = {
    "app.name": str,
    "app.short_name": str,
    "app.version": str,
    "app.author": str,
    "app.roll_no": str,
    "app.course": str,
    "app.quality_goal": str,
    "paths.database": str,
    "paths.log_file": str,
    "paths.export_dir": str,
    "logging.level": str,
    "logging.max_bytes": int,
    "logging.backup_count": int,
    "logging.format": str,
    "ui.appearance_mode": str,
    "ui.color_theme": str,
    "ui.window_width": int,
    "ui.window_height": int,
    "ui.min_width": int,
    "ui.min_height": int,
    "ui.screen_margin": int,
    "ui.sidebar_width": int,
    "ui.font_family": str,
    "ui.font_size": int,
    "ui.heading_size": int,
    "ui.toast_ms": int,
    "ui.search_debounce_ms": int,
    "ui.table_row_height": int,
    "ui.chart_dpi": int,
    "ui.chart_height": int,
    "ui.palette": dict,
    "inventory.currency_symbol": str,
    "inventory.currency_options": list,
    "inventory.default_reorder_level": int,
    "inventory.turnover_period_days": int,
    "inventory.chart_days": int,
    "inventory.default_unit": str,
    "inventory.units": list,
    "display.page_size": int,
    "display.date_format": str,
    "display.date_format_options": list,
    "activity_log.retention_days": int,
    "operator.name": str,
    "operator.role": str,
    "operator.roles": list,
    "validation.page_size_min": int,
    "validation.page_size_max": int,
    "validation.retention_days_min": int,
    "validation.retention_days_max": int,
    "validation.reorder_level_max": int,
    "validation.currency_max_length": int,
    "validation.text_max_length": int,
    "validation.notes_max_length": int,
    "validation.sku_pattern": str,
    "validation.phone_pattern": str,
    "validation.email_pattern": str,
}

# Keys whose value must be one of a fixed set of choices.
CHOICES: dict[str, tuple[str, ...]] = {
    "logging.level": LOG_LEVELS,
    "ui.appearance_mode": APPEARANCE_MODES,
    "ui.color_theme": COLOR_THEMES,
}

# Integer keys that must be strictly positive.
POSITIVE_INTS: tuple[str, ...] = (
    "logging.max_bytes",
    "ui.window_width",
    "ui.window_height",
    "ui.font_size",
    "inventory.turnover_period_days",
    "inventory.chart_days",
    "display.page_size",
    "activity_log.retention_days",
)

# Keys holding regular expressions that must compile.
REGEX_KEYS: tuple[str, ...] = (
    "validation.sku_pattern",
    "validation.phone_pattern",
    "validation.email_pattern",
)

_MISSING = object()


class ConfigError(Exception):
    """Raised when the configuration file is missing, unreadable or invalid."""


class AppConfig:
    """Read-only, validated view over the configuration dictionary.

    Args:
        data: The parsed and validated configuration mapping.
        source: Path of the file the data was loaded from.
    """

    def __init__(self, data: dict[str, Any], source: Path) -> None:
        self._data = data
        self.source = source

    def get(self, dotted_key: str) -> Any:
        """Return the value stored under a dotted key such as ``"ui.font_size"``.

        Args:
            dotted_key: Section and key joined with dots.

        Returns:
            A deep copy of the stored value (callers cannot mutate config).

        Raises:
            ConfigError: If the key does not exist.
        """
        value = _lookup(self._data, dotted_key)
        if value is _MISSING:
            raise ConfigError(f"Unknown configuration key: '{dotted_key}'")
        return copy.deepcopy(value)

    def section(self, name: str) -> dict[str, Any]:
        """Return a copy of a whole top-level section.

        Args:
            name: Section name, e.g. ``"inventory"``.

        Returns:
            A deep copy of the section dictionary.

        Raises:
            ConfigError: If the section does not exist.
        """
        section = self.get(name)
        if not isinstance(section, dict):
            raise ConfigError(f"Configuration key '{name}' is not a section")
        return section

    def resolve_path(self, dotted_key: str) -> Path:
        """Resolve a path setting relative to the project root.

        Args:
            dotted_key: Key holding a relative or absolute path.

        Returns:
            An absolute :class:`~pathlib.Path`.
        """
        path = Path(self.get(dotted_key))
        return path if path.is_absolute() else PROJECT_ROOT / path

    def as_dict(self) -> dict[str, Any]:
        """Return a deep copy of the complete configuration mapping."""
        return copy.deepcopy(self._data)


def _lookup(data: dict[str, Any], dotted_key: str) -> Any:
    """Walk a nested dict along a dotted key; return ``_MISSING`` if absent."""
    node: Any = data
    for part in dotted_key.split("."):
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    return node


def _type_error(key: str, value: Any, expected: type | tuple[type, ...]) -> str | None:
    """Return an error message when ``value`` does not match ``expected``."""
    if value is _MISSING:
        return f"missing required key '{key}'"
    # bool is a subclass of int in Python, so reject it explicitly for int keys.
    if isinstance(value, bool) and expected is not bool:
        return f"'{key}' must be {_type_name(expected)}, got bool"
    if not isinstance(value, expected):
        return f"'{key}' must be {_type_name(expected)}, got {type(value).__name__}"
    return None


def _type_name(expected: type | tuple[type, ...]) -> str:
    """Human-readable name for a type or tuple of types."""
    if isinstance(expected, tuple):
        return " or ".join(t.__name__ for t in expected)
    return expected.__name__


def _value_errors(data: dict[str, Any]) -> list[str]:
    """Check choices, positive integers, regexes and min/max ordering."""
    errors: list[str] = []
    for key, allowed in CHOICES.items():
        value = _lookup(data, key)
        if isinstance(value, str) and value not in allowed:
            errors.append(f"'{key}' must be one of {list(allowed)}, got '{value}'")
    for key in POSITIVE_INTS:
        value = _lookup(data, key)
        if isinstance(value, int) and value <= 0:
            errors.append(f"'{key}' must be greater than 0")
    for key in REGEX_KEYS:
        errors.extend(_regex_error(key, _lookup(data, key)))
    errors.extend(_range_errors(data))
    return errors


def _regex_error(key: str, pattern: Any) -> list[str]:
    """Return a one-item error list when ``pattern`` is not a valid regex."""
    if not isinstance(pattern, str):
        return []
    try:
        re.compile(pattern)
    except re.error as exc:
        return [f"'{key}' is not a valid regular expression: {exc}"]
    return []


def _range_errors(data: dict[str, Any]) -> list[str]:
    """Ensure defaults sit inside the min/max bounds declared in ``validation``."""
    checks = (
        ("display.page_size", "validation.page_size_min", "validation.page_size_max"),
        (
            "activity_log.retention_days",
            "validation.retention_days_min",
            "validation.retention_days_max",
        ),
    )
    errors: list[str] = []
    for key, low_key, high_key in checks:
        value, low, high = (_lookup(data, k) for k in (key, low_key, high_key))
        if all(isinstance(v, int) for v in (value, low, high)) and not low <= value <= high:
            errors.append(f"'{key}' must be between {low} and {high}, got {value}")
    return errors


def validate_config(data: Any) -> None:
    """Validate a parsed configuration mapping against :data:`SCHEMA`.

    Args:
        data: The object produced by ``json.load``.

    Raises:
        ConfigError: Listing every problem found, one per line.
    """
    if not isinstance(data, dict):
        raise ConfigError("Configuration root must be a JSON object")
    errors = [
        message
        for key, expected in SCHEMA.items()
        if (message := _type_error(key, _lookup(data, key), expected))
    ]
    errors.extend(_value_errors(data))
    if errors:
        bullet_list = "\n  - ".join(errors)
        raise ConfigError(f"Invalid configuration file:\n  - {bullet_list}")


def _read_json(path: Path) -> Any:
    """Read and parse a JSON file, converting I/O and syntax errors to ConfigError."""
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ConfigError(f"Configuration file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Configuration file {path.name} is not valid JSON "
            f"(line {exc.lineno}, column {exc.colno}): {exc.msg}"
        ) from exc


def load_config(path: Path | str | None = None) -> AppConfig:
    """Load and validate a configuration file.

    Args:
        path: Optional path to a JSON file; defaults to ``config/config.json``.

    Returns:
        A validated :class:`AppConfig`.

    Raises:
        ConfigError: If the file is missing, malformed or fails validation.
    """
    source = Path(path) if path else DEFAULT_CONFIG_PATH
    data = _read_json(source)
    validate_config(data)
    return AppConfig(data, source)


_cached_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Return the application-wide configuration, loading it on first use.

    Returns:
        The cached :class:`AppConfig` for ``config/config.json``.
    """
    global _cached_config
    if _cached_config is None:
        _cached_config = load_config()
    return _cached_config
