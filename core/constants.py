"""Domain constants shared by every layer (single source of truth for enums).

These values are *domain vocabulary*, not configuration: they describe what an
action or a transaction type **is**, so changing them requires a code change and a
schema migration. Tunable behaviour (thresholds, theme, page size, ...) lives in
``config/config.json`` and the ``settings`` table instead.

The database schema builds its ``CHECK`` constraints from these tuples, so the
Python code and the SQLite schema can never drift apart.

Layer: core (leaf module, imports nothing from the application)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

# Stock movement types stored in ``stock_transactions.type``.
TX_IN = "IN"
TX_OUT = "OUT"
TX_ADJUST = "ADJUST"
TRANSACTION_TYPES: tuple[str, ...] = (TX_IN, TX_OUT, TX_ADJUST)

# Audit-trail actions stored in ``activity_log.action``.
ACTION_CREATE = "CREATE"
ACTION_UPDATE = "UPDATE"
ACTION_DELETE = "DELETE"
ACTION_STOCK_IN = "STOCK_IN"
ACTION_STOCK_OUT = "STOCK_OUT"
ACTION_ADJUST = "ADJUST"
ACTION_SETTINGS_CHANGE = "SETTINGS_CHANGE"
ACTION_LOGIN = "LOGIN"
ACTION_EXPORT = "EXPORT"
ACTION_ERROR = "ERROR"
ACTIONS: tuple[str, ...] = (
    ACTION_CREATE,
    ACTION_UPDATE,
    ACTION_DELETE,
    ACTION_STOCK_IN,
    ACTION_STOCK_OUT,
    ACTION_ADJUST,
    ACTION_SETTINGS_CHANGE,
    ACTION_LOGIN,
    ACTION_EXPORT,
    ACTION_ERROR,
)

# Entity names written to ``activity_log.entity``.
ENTITY_CATEGORY = "Category"
ENTITY_SUPPLIER = "Supplier"
ENTITY_PRODUCT = "Product"
ENTITY_STOCK = "StockTransaction"
ENTITY_SETTING = "Setting"
ENTITY_ACTIVITY_LOG = "ActivityLog"
ENTITY_SYSTEM = "System"

# Standard Python logging level names accepted by config and settings.
LOG_LEVELS: tuple[str, ...] = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

# CustomTkinter appearance modes and built-in colour themes.
APPEARANCE_MODES: tuple[str, ...] = ("light", "dark", "system")
COLOR_THEMES: tuple[str, ...] = ("blue", "green", "dark-blue")

# Value types a runtime setting may declare in ``settings.value_type``.
VALUE_TYPES: tuple[str, ...] = ("str", "int", "float", "bool")

# Storage format for every timestamp column (sortable ISO-8601, local time).
DB_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
DB_DATE_FORMAT = "%Y-%m-%d"
