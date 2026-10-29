"""Tests for :mod:`config.config_loader` (QO2: zero hard-coded configuration).

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from config.config_loader import (
    DEFAULT_CONFIG_PATH,
    PROJECT_ROOT,
    ConfigError,
    get_config,
    load_config,
)


def _write(tmp_path: Path, data: object) -> Path:
    """Write ``data`` as JSON into a temporary config file and return its path."""
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _default_data() -> dict:
    """Return a fresh copy of the shipped configuration."""
    return json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))


def test_shipped_config_is_valid() -> None:
    """The committed config.json must pass validation."""
    config = load_config()
    assert config.get("app.roll_no") == "240302054"
    assert config.get("display.page_size") > 0


def test_get_returns_copy_so_config_is_read_only() -> None:
    """Mutating a returned section must not change the stored configuration."""
    config = load_config()
    palette = config.get("ui.palette")
    palette["danger"] = "#000000"
    assert config.get("ui.palette")["danger"] != "#000000"


def test_resolve_path_is_relative_to_project_root() -> None:
    """Relative paths resolve against the project root."""
    config = load_config()
    assert config.resolve_path("paths.database") == PROJECT_ROOT / "data" / "inventory.db"


def test_unknown_key_raises() -> None:
    """Asking for a key that does not exist fails loudly."""
    with pytest.raises(ConfigError, match="Unknown configuration key"):
        load_config().get("ui.does_not_exist")


def test_section_returns_dict() -> None:
    """``section`` returns the whole top-level mapping."""
    assert "currency_symbol" in load_config().section("inventory")


def test_missing_file_raises(tmp_path: Path) -> None:
    """A missing file produces a clear message."""
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.json")


def test_invalid_json_reports_line(tmp_path: Path) -> None:
    """Malformed JSON reports the line and column of the syntax error."""
    path = tmp_path / "config.json"
    path.write_text('{"app": {"name": "x",}}', encoding="utf-8")
    with pytest.raises(ConfigError, match="line 1"):
        load_config(path)


def test_missing_key_is_reported(tmp_path: Path) -> None:
    """Removing a required key is detected."""
    data = _default_data()
    del data["inventory"]["currency_symbol"]
    with pytest.raises(ConfigError, match="inventory.currency_symbol"):
        load_config(_write(tmp_path, data))


def test_wrong_type_is_reported(tmp_path: Path) -> None:
    """A string where an int is expected is rejected."""
    data = _default_data()
    data["display"]["page_size"] = "fifteen"
    with pytest.raises(ConfigError, match="display.page_size' must be int"):
        load_config(_write(tmp_path, data))


def test_bool_is_not_accepted_as_int(tmp_path: Path) -> None:
    """``true`` must not sneak through as the integer 1."""
    data = _default_data()
    data["logging"]["backup_count"] = True
    with pytest.raises(ConfigError, match="got bool"):
        load_config(_write(tmp_path, data))


def test_invalid_choice_is_reported(tmp_path: Path) -> None:
    """Values outside the allowed set are rejected."""
    data = _default_data()
    data["logging"]["level"] = "LOUD"
    with pytest.raises(ConfigError, match="logging.level"):
        load_config(_write(tmp_path, data))


def test_out_of_range_page_size_is_reported(tmp_path: Path) -> None:
    """Defaults must respect the declared validation bounds."""
    data = _default_data()
    data["display"]["page_size"] = 1000
    with pytest.raises(ConfigError, match="between"):
        load_config(_write(tmp_path, data))


def test_bad_regex_is_reported(tmp_path: Path) -> None:
    """Regex settings must compile."""
    data = _default_data()
    data["validation"]["sku_pattern"] = "([A-Z"
    with pytest.raises(ConfigError, match="regular expression"):
        load_config(_write(tmp_path, data))


def test_all_errors_reported_together(tmp_path: Path) -> None:
    """Several problems are listed in one error, not one per run."""
    data = _default_data()
    data["display"]["page_size"] = "x"
    data["ui"]["appearance_mode"] = "neon"
    with pytest.raises(ConfigError) as info:
        load_config(_write(tmp_path, data))
    assert "page_size" in str(info.value) and "appearance_mode" in str(info.value)


def test_root_must_be_object(tmp_path: Path) -> None:
    """A JSON array at the root is rejected."""
    with pytest.raises(ConfigError, match="JSON object"):
        load_config(_write(tmp_path, [1, 2, 3]))


def test_get_config_is_cached() -> None:
    """``get_config`` returns the same instance on repeated calls."""
    assert get_config() is get_config()
