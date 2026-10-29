"""Tests for derived values on the model dataclasses.

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from models import ActivityLog, ListQuery, Page, Product, StockTransaction


def test_product_low_stock_and_value() -> None:
    """Stock at the reorder level counts as low; value is qty x cost."""
    product = Product(quantity_on_hand=5, reorder_level=5, unit_cost=2.5)
    assert product.is_low_stock and not product.is_out_of_stock
    assert product.stock_value == 12.5


def test_product_from_row_converts_flags() -> None:
    """SQLite 0/1 becomes a bool and NULL supplier name becomes ''."""
    product = Product.from_row({"id": 1, "is_active": 0, "supplier_name": None, "extra": 1})
    assert product.is_active is False and product.supplier_name == ""


def test_editable_values_excludes_quantity() -> None:
    """Quantity is never part of an editable payload."""
    assert "quantity_on_hand" not in Product().editable_values()


def test_transaction_value_is_positive_for_negative_adjust() -> None:
    """A negative adjustment still has a positive monetary value."""
    assert StockTransaction(quantity=-4, unit_cost=10).value == 40


def test_activity_details_handles_bad_json() -> None:
    """Corrupt payloads are surfaced, not raised."""
    assert ActivityLog(details_json="{oops").details == {"raw": "{oops"}
    assert ActivityLog(details_json='{"a": 1}').details == {"a": 1}


def test_page_maths() -> None:
    """Page count rounds up and never drops below one."""
    assert Page(total=31, page_size=15).pages == 3
    assert Page(total=0, page_size=15).pages == 1
    assert Page(total=31, page=3, page_size=15).has_next is False
    assert ListQuery(page=3, page_size=10).offset == 20
