"""SQLite schema definition and ordered migrations.

The ``CHECK`` constraints are generated from :mod:`core.constants`, so the
Python enums and the database can never drift apart. To change the schema,
append a new version to :data:`MIGRATIONS`; ``Database.initialize`` upgrades
existing databases on the next start.

Layer: core
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from core.constants import ACTIONS, LOG_LEVELS, TRANSACTION_TYPES, VALUE_TYPES


def _sql_list(values: tuple[str, ...]) -> str:
    """Render a tuple of constants as a SQL ``IN`` list: ``'A', 'B'``."""
    return ", ".join(f"'{value}'" for value in values)


_NOW = "(strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))"

SCHEMA_V1: list[str] = [
    f"""
    CREATE TABLE IF NOT EXISTS categories (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
        description TEXT    NOT NULL DEFAULT '',
        created_at  TEXT    NOT NULL DEFAULT {_NOW},
        updated_at  TEXT    NOT NULL DEFAULT {_NOW}
    )""",
    f"""
    CREATE TABLE IF NOT EXISTS suppliers (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        name           TEXT NOT NULL COLLATE NOCASE,
        contact_person TEXT NOT NULL DEFAULT '',
        phone          TEXT NOT NULL DEFAULT '',
        email          TEXT NOT NULL DEFAULT '',
        address        TEXT NOT NULL DEFAULT '',
        created_at     TEXT NOT NULL DEFAULT {_NOW},
        updated_at     TEXT NOT NULL DEFAULT {_NOW}
    )""",
    f"""
    CREATE TABLE IF NOT EXISTS products (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        sku              TEXT    NOT NULL UNIQUE COLLATE NOCASE,
        name             TEXT    NOT NULL COLLATE NOCASE,
        category_id      INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
        supplier_id      INTEGER REFERENCES suppliers(id) ON DELETE RESTRICT,
        unit             TEXT    NOT NULL,
        unit_cost        REAL    NOT NULL DEFAULT 0 CHECK (unit_cost >= 0),
        selling_price    REAL    NOT NULL DEFAULT 0 CHECK (selling_price >= 0),
        quantity_on_hand INTEGER NOT NULL DEFAULT 0 CHECK (quantity_on_hand >= 0),
        reorder_level    INTEGER NOT NULL DEFAULT 0 CHECK (reorder_level >= 0),
        is_active        INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
        created_at       TEXT    NOT NULL DEFAULT {_NOW},
        updated_at       TEXT    NOT NULL DEFAULT {_NOW}
    )""",
    f"""
    CREATE TABLE IF NOT EXISTS stock_transactions (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id     INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
        type           TEXT    NOT NULL CHECK (type IN ({_sql_list(TRANSACTION_TYPES)})),
        quantity       INTEGER NOT NULL CHECK (quantity <> 0),
        unit_cost      REAL    NOT NULL DEFAULT 0 CHECK (unit_cost >= 0),
        reference_note TEXT    NOT NULL DEFAULT '',
        performed_by   TEXT    NOT NULL DEFAULT '',
        created_at     TEXT    NOT NULL DEFAULT {_NOW},
        -- IN / OUT store a positive quantity; ADJUST stores a signed delta.
        CHECK (type = 'ADJUST' OR quantity > 0)
    )""",
    f"""
    CREATE TABLE IF NOT EXISTS activity_log (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp    TEXT NOT NULL DEFAULT {_NOW},
        user         TEXT NOT NULL DEFAULT '',
        action       TEXT NOT NULL CHECK (action IN ({_sql_list(ACTIONS)})),
        entity       TEXT NOT NULL DEFAULT '',
        entity_id    TEXT,
        details_json TEXT NOT NULL DEFAULT '{{}}',
        level        TEXT NOT NULL DEFAULT 'INFO' CHECK (level IN ({_sql_list(LOG_LEVELS)}))
    )""",
    f"""
    CREATE TABLE IF NOT EXISTS settings (
        key         TEXT PRIMARY KEY,
        value       TEXT NOT NULL,
        value_type  TEXT NOT NULL DEFAULT 'str' CHECK (value_type IN ({_sql_list(VALUE_TYPES)})),
        description TEXT NOT NULL DEFAULT '',
        updated_at  TEXT NOT NULL DEFAULT {_NOW}
    )""",
    "CREATE INDEX IF NOT EXISTS idx_categories_created ON categories(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name)",
    "CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)",
    "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_products_supplier ON products(supplier_id)",
    "CREATE INDEX IF NOT EXISTS idx_products_created ON products(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_tx_product ON stock_transactions(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_tx_created ON stock_transactions(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_tx_type ON stock_transactions(type)",
    "CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_activity_action ON activity_log(action)",
    "CREATE INDEX IF NOT EXISTS idx_activity_entity ON activity_log(entity)",
]

# Ordered schema migrations: version number -> statements that reach it.
MIGRATIONS: dict[int, list[str]] = {1: SCHEMA_V1}
