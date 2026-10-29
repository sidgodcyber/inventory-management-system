"""Validation of a parsed configuration mapping against :mod:`config.schema`.

Every problem is collected before raising, so a broken ``config.json`` is
reported in full and the user can fix it in a single edit.

Layer: config
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import re
from typing import Any

from config.schema import CHOICES, POSITIVE_INTS, RANGE_CHECKS, REGEX_KEYS, SCHEMA

#: Sentinel returned by :func:`lookup` for keys that do not exist.
MISSING = object()


class ConfigError(Exception):
    """Raised when the configuration file is missing, unreadable or invalid."""


def lookup(data: Any, dotted_key: str) -> Any:
    """Walk a nested mapping along a dotted key.

    Args:
        data: Parsed configuration (nested dictionaries).
        dotted_key: Section and key joined with dots, e.g. ``"ui.font_size"``.

    Returns:
        The stored value, or :data:`MISSING` when any part of the path is absent.
    """
    node: Any = data
    for part in dotted_key.split("."):
        if not isinstance(node, dict) or part not in node:
            return MISSING
        node = node[part]
    return node


def _type_name(expected: type | tuple[type, ...]) -> str:
    """Human-readable name for a type or tuple of types."""
    if isinstance(expected, tuple):
        return " or ".join(t.__name__ for t in expected)
    return expected.__name__


def type_error(key: str, value: Any, expected: type | tuple[type, ...]) -> str | None:
    """Describe a missing or wrongly typed value.

    Args:
        key: Dotted key being checked.
        value: The value found (or :data:`MISSING`).
        expected: Required type(s).

    Returns:
        An error message, or ``None`` when the value is acceptable.
    """
    if value is MISSING:
        return f"missing required key '{key}'"
    # bool is a subclass of int in Python, so reject it explicitly for int keys.
    if isinstance(value, bool) and expected is not bool:
        return f"'{key}' must be {_type_name(expected)}, got bool"
    if not isinstance(value, expected):
        return f"'{key}' must be {_type_name(expected)}, got {type(value).__name__}"
    return None


def value_errors(data: dict[str, Any]) -> list[str]:
    """Check allowed choices, positive integers, regexes and min/max ranges.

    Args:
        data: Parsed configuration whose types are already valid.

    Returns:
        One message per problem (empty when everything is valid).
    """
    errors = [f"'{key}' must be one of {list(allowed)}, got '{lookup(data, key)}'"
              for key, allowed in CHOICES.items()
              if isinstance(lookup(data, key), str) and lookup(data, key) not in allowed]
    errors += [f"'{key}' must be greater than 0" for key in POSITIVE_INTS
               if isinstance(lookup(data, key), int) and lookup(data, key) <= 0]
    for key in REGEX_KEYS:
        errors.extend(_regex_error(key, lookup(data, key)))
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
    errors: list[str] = []
    for key, low_key, high_key in RANGE_CHECKS:
        value, low, high = (lookup(data, k) for k in (key, low_key, high_key))
        if all(isinstance(v, int) for v in (value, low, high)) and not low <= value <= high:
            errors.append(f"'{key}' must be between {low} and {high}, got {value}")
    return errors


def validate_config(data: Any) -> None:
    """Validate a parsed configuration mapping against :data:`config.schema.SCHEMA`.

    Args:
        data: The object produced by ``json.load``.

    Raises:
        ConfigError: Listing every problem found, one per line.
    """
    if not isinstance(data, dict):
        raise ConfigError("Configuration root must be a JSON object")
    errors = [message for key, expected in SCHEMA.items()
              if (message := type_error(key, lookup(data, key), expected))]
    errors.extend(value_errors(data))
    if errors:
        bullet_list = "\n  - ".join(errors)
        raise ConfigError(f"Invalid configuration file:\n  - {bullet_list}")
