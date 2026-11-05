"""Tests for what the dashboard says and how the stock runway orders products.

Layer: tests
Author: Siddhi Baluja
"""

from __future__ import annotations

from models.product import Product
from models.reports import DashboardStats
from ui.views.dashboard import finding
from ui.views.dashboard_runway import by_urgency, next_to_run_out, order_at_least


def _stats(low: int, out: int) -> DashboardStats:
    """Dashboard figures with the given low-stock and stockout counts."""
    return DashboardStats(40, 1000.0, low, out, 2.0, 90)


def test_finding_names_stockouts_first() -> None:
    """Stockouts lead; the low count excludes them, so the two add up."""
    assert finding(_stats(6, 4)) == ("4 products are out of stock and 2 more are at or below "
                                     "their reorder level.")


def test_finding_without_stockouts_and_when_healthy() -> None:
    """The sentence changes with the data."""
    assert finding(_stats(3, 0)) == "3 products are at or below their reorder level."
    assert finding(_stats(0, 0)) == "Every product is above its reorder level."


def test_order_at_least_lifts_stock_above_reorder_level() -> None:
    """Ordering this much leaves the product above its level."""
    product = Product(quantity_on_hand=7, reorder_level=10)
    assert product.quantity_on_hand + order_at_least(product) > product.reorder_level


def test_by_urgency_puts_stockouts_first() -> None:
    """The lowest share of the reorder level comes first."""
    near = Product(name="Near", quantity_on_hand=9, reorder_level=10)
    half = Product(name="Half", quantity_on_hand=5, reorder_level=10)
    empty = Product(name="Empty", quantity_on_hand=0, reorder_level=40)
    assert [p.name for p in by_urgency([near, half, empty])] == ["Empty", "Half", "Near"]


def test_next_to_run_out_skips_low_and_unused_products() -> None:
    """Only healthy products with a usage rate qualify, soonest first, up to the count."""
    soon = Product(id=1, quantity_on_hand=50, reorder_level=10)
    later = Product(id=2, quantity_on_hand=50, reorder_level=10)
    unused = Product(id=3, quantity_on_hand=50, reorder_level=10)
    low = Product(id=4, quantity_on_hand=5, reorder_level=10)
    days = {1: 4.0, 2: 9.0, 3: None, 4: 1.0}
    assert next_to_run_out([later, unused, low, soon], days, 5) == [soon, later]
    assert next_to_run_out([soon, later], days, 1) == [soon]
    assert next_to_run_out([soon], days, -2) == []
