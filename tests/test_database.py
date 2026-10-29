"""Tests for :mod:`core.database`: schema, constraints and transactions.

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import pytest

from core.database import MIGRATIONS, Database
from core.exceptions import DatabaseError

EXPECTED_TABLES = {
    "categories",
    "suppliers",
    "products",
    "stock_transactions",
    "activity_log",
    "settings",
}


def _add_category(db: Database, name: str = "Tools") -> int:
    """Insert a category and return its id."""
    return int(db.execute("INSERT INTO categories (name) VALUES (?)", (name,)).lastrowid)


def test_initialize_creates_all_tables(db: Database) -> None:
    """Every table from the design is created."""
    rows = db.query_all("SELECT name FROM sqlite_master WHERE type = 'table'")
    assert EXPECTED_TABLES <= {row["name"] for row in rows}


def test_initialize_sets_latest_version_and_is_idempotent(db: Database) -> None:
    """Running migrations twice is harmless and reports the latest version."""
    assert db.schema_version == max(MIGRATIONS)
    assert db.initialize() == max(MIGRATIONS)


def test_foreign_keys_are_enforced(db: Database) -> None:
    """A product cannot reference a missing category."""
    with pytest.raises(DatabaseError, match="FOREIGN KEY"):
        db.execute(
            "INSERT INTO products (sku, name, category_id, unit) VALUES ('A1', 'x', 999, 'pcs')"
        )


def test_quantity_cannot_be_negative(db: Database) -> None:
    """The schema itself refuses negative stock (defence in depth)."""
    category_id = _add_category(db)
    with pytest.raises(DatabaseError, match="CHECK"):
        db.execute(
            "INSERT INTO products (sku, name, category_id, unit, quantity_on_hand) "
            "VALUES ('A1', 'x', ?, 'pcs', -1)",
            (category_id,),
        )


def test_invalid_activity_action_rejected(db: Database) -> None:
    """Only the actions listed in core.constants are accepted."""
    with pytest.raises(DatabaseError, match="CHECK"):
        db.execute("INSERT INTO activity_log (action) VALUES ('HACK')")


def test_out_transaction_requires_positive_quantity(db: Database) -> None:
    """IN/OUT rows store a positive quantity; only ADJUST may be negative."""
    category_id = _add_category(db)
    product_id = db.execute(
        "INSERT INTO products (sku, name, category_id, unit) VALUES ('A1', 'x', ?, 'pcs')",
        (category_id,),
    ).lastrowid
    with pytest.raises(DatabaseError):
        db.execute(
            "INSERT INTO stock_transactions (product_id, type, quantity) VALUES (?, 'OUT', -5)",
            (product_id,),
        )
    db.execute(
        "INSERT INTO stock_transactions (product_id, type, quantity) VALUES (?, 'ADJUST', -5)",
        (product_id,),
    )


def test_transaction_rolls_back_on_error(db: Database) -> None:
    """An exception inside a transaction undoes every statement in it."""
    with pytest.raises(RuntimeError):
        with db.transaction():
            _add_category(db, "Rolled back")
            raise RuntimeError("boom")
    assert db.query_value("SELECT COUNT(*) FROM categories") == 0


def test_nested_transaction_commits_once(db: Database) -> None:
    """Inner blocks join the outer transaction instead of committing early."""
    with db.transaction():
        with db.transaction():
            _add_category(db, "Inner")
        assert db.in_transaction
        _add_category(db, "Outer")
    assert not db.in_transaction
    assert db.query_value("SELECT COUNT(*) FROM categories") == 2


def test_query_value_default(db: Database) -> None:
    """``query_value`` falls back to the default when there is no row."""
    assert db.query_value("SELECT name FROM categories WHERE id = -1", default="none") == "none"


def test_category_name_unique_case_insensitive(db: Database) -> None:
    """Category names are unique regardless of letter case."""
    _add_category(db, "Hardware")
    with pytest.raises(DatabaseError, match="UNIQUE"):
        _add_category(db, "hardware")
