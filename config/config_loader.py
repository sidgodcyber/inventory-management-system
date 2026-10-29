"""Single access point for application configuration (``config/config.json``).

The loader reads the JSON file once, validates it (see :mod:`config.validation`
and :mod:`config.schema`) and exposes the values through :class:`AppConfig`. A
broken or incomplete file fails fast with a :class:`ConfigError` listing
*every* problem, so the user can fix the file in one go.

Layer: config (usable by every layer)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from config.validation import MISSING, ConfigError, lookup, validate_config

__all__ = ["DEFAULT_CONFIG_PATH", "PROJECT_ROOT", "AppConfig", "ConfigError", "get_config",
           "load_config", "validate_config"]

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH: Path = PROJECT_ROOT / "config" / "config.json"


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
        value = lookup(self._data, dotted_key)
        if value is MISSING:
            raise ConfigError(f"Unknown configuration key: '{dotted_key}'")
        return copy.deepcopy(value)

    def section(self, name: str) -> dict[str, Any]:
        """Return a copy of a whole top-level section.

        Args:
            name: Section name, e.g. ``"inventory"``.

        Returns:
            A deep copy of the section dictionary.

        Raises:
            ConfigError: If the section does not exist or is not a mapping.
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
        """Return a deep copy of the complete configuration mapping.

        Returns:
            Nested dictionaries mirroring ``config.json``.
        """
        return copy.deepcopy(self._data)


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
