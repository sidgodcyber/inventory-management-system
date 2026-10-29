"""Tests for :mod:`repositories.stock_transaction_repository`.

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from datetime import date

import pytest

from core.database import Database
from models.common import ListQuery
from models.filters import TransactionFilter
from models.product import Product
from models.stock_transaction import StockTransaction
from repositories.category_repository import CategoryRepository
from repositories.product_repository import ProductRepository
from repositories.stock_transaction_repository import StockTransactionRepository


@pytest.fixture()
def repo(db: Database) -> StockTransactionRepository:
    """Repository bound to the temporary database."""
    return StockTransactionRepository(db)


@pytest.fixture()
def product_id(db: Database) -> int:
    """Id of a saved product."""
    category = CategoryRepository(db).create("General", "")
    return ProductRepository(db).create(
        Product(sku="GEN-1", name="Widget", category_id=category, unit="pcs", unit_cost=10)
    )


def _tx(product_id: int, kind: str, qty: int, when: str, cost: float = 10.0) -> StockTransaction:
    """Build an unsaved movement."""
    return StockTransaction(product_id=product_id, type=kind, quantity=qty,
                            unit_cost=cost, performed_by="Tester", created_at=when)


@pytest.fixture()
def history(repo: StockTransactionRepository, product_id: int) -> None:
    """Three movements spread over three days."""
    repo.create(_tx(product_id, "IN", 100, "2026-01-01 09:00:00"))
    repo.create(_tx(product_id, "OUT", 30, "2026-01-02 10:00:00"))
    repo.create(_tx(product_id, "ADJUST", -5, "2026-01-03 11:00:00"))


def test_create_and_get_joins_product(repo: StockTransactionRepository, product_id: int) -> None:
    """Movements carry the product SKU and name."""
    tx_id = repo.create(_tx(product_id, "IN", 5, ""))
    tx = repo.get(tx_id)
    assert tx.product_sku == "GEN-1" and tx.created_at
    assert repo.count_for_product(product_id) == 1


@pytest.mark.usefixtures("history")
def test_find_filters_by_type_and_dates(repo: StockTransactionRepository) -> None:
    """Type and inclusive date bounds narrow the history."""
    assert repo.find(TransactionFilter(tx_type="OUT"), ListQuery()).total == 1
    in_range = TransactionFilter(date_from=date(2026, 1, 2), date_to=date(2026, 1, 3))
    assert repo.find(in_range, ListQuery()).total == 2
    newest = repo.find(TransactionFilter(), ListQuery(sort_by="created_at", descending=True))
    assert newest.items[0].type == "ADJUST"


@pytest.mark.usefixtures("history")
def test_list_filtered_newest_first(repo: StockTransactionRepository) -> None:
    """Export list is ordered newest first."""
    assert [t.type for t in repo.list_filtered(TransactionFilter())] == ["ADJUST", "OUT", "IN"]


@pytest.mark.usefixtures("history")
def test_issues_by_product(repo: StockTransactionRepository, product_id: int) -> None:
    """COGS counts only OUT movements within the window."""
    issues = repo.issues_by_product("2026-01-01 00:00:00", "2026-01-31 23:59:59")
    assert issues == {product_id: (30, 300.0)}


@pytest.mark.usefixtures("history")
def test_net_change_after(repo: StockTransactionRepository, product_id: int) -> None:
    """Signed delta: -30 (OUT) + -5 (ADJUST) after the opening IN."""
    assert repo.net_change_after("2026-01-01 12:00:00") == {product_id: -35}


@pytest.mark.usefixtures("history")
def test_daily_totals_exclude_adjustments(repo: StockTransactionRepository) -> None:
    """The in-vs-out chart ignores adjustments."""
    totals = repo.daily_totals("2026-01-01 00:00:00", "2026-01-31 23:59:59")
    assert totals == [("2026-01-01", "IN", 100), ("2026-01-02", "OUT", 30)]


@pytest.mark.usefixtures("history")
def test_daily_net_change(repo: StockTransactionRepository, product_id: int) -> None:
    """Signed per-day deltas within the window."""
    rows = repo.daily_net_change("2026-01-02 00:00:00", "2026-01-31 23:59:59")
    assert rows == [(product_id, "2026-01-02", -30), (product_id, "2026-01-03", -5)]
