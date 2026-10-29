"""SQLite connection management, schema creation and migrations.

:class:`Database` owns one connection per application run (Tkinter is
single-threaded). Writes are grouped with :meth:`Database.transaction`, which is
re-entrant: only the outermost block issues ``BEGIN``/``COMMIT``/``ROLLBACK``.
This lets a service wrap several repository calls into one atomic unit while
each repository method stays individually safe to call.

The schema itself lives in :mod:`core.schema` and is versioned with
``PRAGMA user_version``; :meth:`Database.initialize` applies pending migrations.

Layer: core (bottom layer; repositories are its only callers)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from core.exceptions import DatabaseError
from core.schema import MIGRATIONS

Params = Sequence[Any] | dict[str, Any]


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
        outermost = self._depth == 0
        if outermost:
            connection.execute("BEGIN")
        self._depth += 1
        try:
            yield connection
        except BaseException:
            if outermost:
                connection.execute("ROLLBACK")
            raise
        else:
            if outermost:
                connection.execute("COMMIT")
        finally:
            self._depth -= 1

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
        """Run a SELECT and return every row.

        Args:
            sql: Parameterised SELECT statement.
            params: Positional or named parameters.

        Returns:
            All matching rows (accessible by column name).
        """
        return self.execute(sql, params).fetchall()

    def query_one(self, sql: str, params: Params = ()) -> sqlite3.Row | None:
        """Run a SELECT and return the first row.

        Args:
            sql: Parameterised SELECT statement.
            params: Positional or named parameters.

        Returns:
            The first row, or ``None`` when nothing matches.
        """
        return self.execute(sql, params).fetchone()

    def query_value(self, sql: str, params: Params = (), default: Any = None) -> Any:
        """Run a SELECT and return the first column of the first row.

        Args:
            sql: Parameterised SELECT statement.
            params: Positional or named parameters.
            default: Returned when there is no row or the value is NULL.

        Returns:
            The scalar value or ``default``.
        """
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
