"""Declarative schema for ``config/config.json``: required keys and value rules.

Adding a new configurable value means adding one line here; the validator in
:mod:`config.validation` then checks it automatically on every start-up.

Layer: config (data only)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from core.constants import APPEARANCE_MODES, COLOR_THEMES, LOG_LEVELS

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
    "ui.mono_font_family": str,
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
    "inventory.report_periods": list,
    "inventory.days_of_stock_warning": int,
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

# (value key, minimum key, maximum key): defaults must sit inside their bounds.
RANGE_CHECKS: tuple[tuple[str, str, str], ...] = (
    ("display.page_size", "validation.page_size_min", "validation.page_size_max"),
    ("activity_log.retention_days", "validation.retention_days_min",
     "validation.retention_days_max"),
)
