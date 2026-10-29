"""Tests for :mod:`repositories.product_repository`.

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import pytest

from core.database import Database
from models.common import ListQuery
from models.product import Product
from repositories.category_repository import CategoryRepository
from repositories.product_repository import ProductRepository


@pytest.fixture()
def repo(db: Database) -> ProductRepository:
    """Repository bound to the temporary database."""
    return ProductRepository(db)


@pytest.fixture()
def category_id(db: Database) -> int:
    """Id of a freshly created category."""
    return CategoryRepository(db).create("Stationery", "")


def _product(category_id: int, sku: str = "PEN-001", **extra: object) -> Product:
    """Build an unsaved product."""
    values = dict(sku=sku, name=f"Item {sku}", category_id=category_id, unit="pcs",
                  unit_cost=10.0, selling_price=15.0, reorder_level=5)
    values.update(extra)
    return Product(**values)


def test_create_starts_with_zero_stock(repo: ProductRepository, category_id: int) -> None:
    """Quantity cannot be set on creation; it comes from stock transactions."""
    new_id = repo.create(_product(category_id))
    product = repo.get(new_id)
    assert product.quantity_on_hand == 0 and product.category_name == "Stationery"
    assert repo.get_by_sku("pen-001").id == new_id


def test_update_does_not_touch_quantity(repo: ProductRepository, category_id: int) -> None:
    """Editing a product leaves stock unchanged."""
    new_id = repo.create(_product(category_id))
    repo.set_quantity(new_id, 40)
    product = repo.get(new_id)
    product.name, product.quantity_on_hand = "Blue pen", 999
    repo.update(product)
    stored = repo.get(new_id)
    assert (stored.name, stored.quantity_on_hand) == ("Blue pen", 40)


def test_soft_delete_hides_from_default_list(repo: ProductRepository, category_id: int) -> None:
    """Inactive products only appear when asked for."""
    new_id = repo.create(_product(category_id))
    repo.set_active(new_id, False)
    assert repo.find(ListQuery()).total == 0
    assert repo.find(ListQuery(), include_inactive=True).total == 1


def test_low_stock_filter_and_summary(repo: ProductRepository, category_id: int) -> None:
    """Low-stock and stockout counts follow qty <= reorder level."""
    healthy, low, empty = (repo.create(_product(category_id, f"SKU-{i}")) for i in range(3))
    repo.set_quantity(healthy, 50)
    repo.set_quantity(low, 5)
    assert {p.id for p in repo.low_stock()} == {low, empty}
    assert repo.find(ListQuery(), low_stock_only=True).total == 2
    summary = repo.stock_summary()
    assert summary["low_stock_count"] == 2 and summary["stockout_count"] == 1
    assert summary["total_value"] == pytest.approx(550.0)
    assert repo.count_low_stock() == 2


def test_value_by_category(repo: ProductRepository, db: Database, category_id: int) -> None:
    """Stock value is grouped per category."""
    other = CategoryRepository(db).create("Hardware", "")
    repo.set_quantity(repo.create(_product(category_id, "A-1")), 10)
    repo.set_quantity(repo.create(_product(other, "B-1", unit_cost=100.0)), 2)
    assert repo.value_by_category() == [("Hardware", 200.0), ("Stationery", 100.0)]


def test_find_filters_by_category_and_search(
    repo: ProductRepository, db: Database, category_id: int
) -> None:
    """Category filter and free-text search combine."""
    other = CategoryRepository(db).create("Hardware", "")
    repo.create(_product(category_id, "PEN-1"))
    repo.create(_product(other, "HAM-1"))
    assert repo.find(ListQuery(), category_id=other).total == 1
    assert repo.find(ListQuery(search="hardware")).total == 1


def test_sort_by_stock_value(repo: ProductRepository, category_id: int) -> None:
    """Computed sort keys work."""
    first = repo.create(_product(category_id, "A-1"))
    second = repo.create(_product(category_id, "B-1"))
    repo.set_quantity(second, 10)
    page = repo.find(ListQuery(sort_by="stock_value", descending=True))
    assert [p.id for p in page.items] == [second, first]
    assert repo.has_transactions(first) is False
