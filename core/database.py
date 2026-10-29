"""SQLite connection management, schema creation and migrations.

:class:`Database` owns one connection per application run (Tkinter is
single-threaded). Writes are grouped with :meth:`Database.transaction`, which is
re-entrant: only the outermost block issues ``BEGIN``/``COMMIT``/``ROLLBACK``.
This lets a service wrap several repository calls into one atomic unit while
each repository method stays individually safe to call.

The schema is versioned with ``PRAGMA user_version``. To change it, append a
new entry to :data:`MIGRATIONS`; existing databases upgrade on next start.

Layer: core (bottom layer; repositories are its only callers)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from core.constants import ACTIONS, LOG_LEVELS, TRANSACTION_TYPES, VALUE_TYPES
from core.exceptions import DatabaseError

Params = Sequence[Any] | dict[str, Any]


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


class Database:
    """Thin wrapper around a single SQLite connection.

    Args:
        path: File path of the database, or ``":memory:"`` for tests.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        self._connection: sqlite3.Connection | None = None
        self._depth = 0  # nesting level of transaction() blocks

    # -- connection -------------------------------------------------------
    @property
    def connection(self) -> sqlite3.Connection:
        """Return the open connection, connecting lazily on first use."""
        if self._connection is None:
            self._connection = self._connect()
        return self._connection

    def _connect(self) -> sqlite3.Connection:
        """Open the connection with row access by name and FK enforcement."""
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None -> autocommit; transactions are explicit below.
        connection = sqlite3.connect(self.path, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def close(self) -> None:
        """Close the connection if it is open."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    # -- transactions -----------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Group statements into one atomic unit (re-entrant).

        Yields:
            The underlying connection.

        Raises:
            Exception: Whatever the block raised, after rolling back.
        """
        connection = self.connection
        if self._depth == 0:
            connection.execute("BEGIN")
        self._depth += 1
        try:
            yield connection
        except BaseException:
            self._depth -= 1
            if self._depth == 0:
                connection.execute("ROLLBACK")
            raise
        self._depth -= 1
        if self._depth == 0:
            connection.execute("COMMIT")

    @property
    def in_transaction(self) -> bool:
        """True while inside at least one :meth:`transaction` block."""
        return self._depth > 0

    # -- query helpers (used by repositories only) -----------------------
    def execute(self, sql: str, params: Params = ()) -> sqlite3.Cursor:
        """Execute one statement, translating driver errors.

        Args:
            sql: Parameterised SQL statement.
            params: Positional or named parameters.

        Returns:
            The cursor, e.g. to read ``lastrowid`` or ``rowcount``.

        Raises:
            DatabaseError: If SQLite rejects the statement.
        """
        try:
            return self.connection.execute(sql, params)
        except sqlite3.Error as exc:
            raise DatabaseError(f"Database error: {exc}") from exc

    def query_all(self, sql: str, params: Params = ()) -> list[sqlite3.Row]:
        """Run a SELECT and return every row."""
        return self.execute(sql, params).fetchall()

    def query_one(self, sql: str, params: Params = ()) -> sqlite3.Row | None:
        """Run a SELECT and return the first row, or ``None``."""
        return self.execute(sql, params).fetchone()

    def query_value(self, sql: str, params: Params = (), default: Any = None) -> Any:
        """Run a SELECT and return the first column of the first row."""
        row = self.query_one(sql, params)
        return default if row is None or row[0] is None else row[0]

    # -- schema -----------------------------------------------------------
    @property
    def schema_version(self) -> int:
        """Current schema version stored in ``PRAGMA user_version``."""
        return int(self.query_value("PRAGMA user_version", default=0))

    def initialize(self) -> int:
        """Create the schema or upgrade it to the latest version.

        Returns:
            The schema version after all pending migrations ran.
        """
        current = self.schema_version
        for version in sorted(v for v in MIGRATIONS if v > current):
            with self.transaction():
                for statement in MIGRATIONS[version]:
                    self.execute(statement)
                # PRAGMA values cannot be bound as parameters; version is an int.
                self.execute(f"PRAGMA user_version = {int(version)}")
        return self.schema_version
