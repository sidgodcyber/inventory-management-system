"""Tests for the stock and product services: stock rules, soft delete, audit.

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from core.exceptions import StockError, ValidationError
from models.common import ListQuery
from models.filters import TransactionFilter
from services.container import AppServices


@pytest.fixture()
def category_id(services: AppServices) -> int:
    """A saved category."""
    return services.categories.create("Stationery").id


def _form(category_id: int, sku: str = "STA-PEN-001", **extra: object) -> dict:
    """Valid product form values."""
    data = {"sku": sku, "name": "Ball pen", "category_id": category_id, "supplier_id": "",
            "unit": "pcs", "unit_cost": "10", "selling_price": "15", "reorder_level": "5"}
    data.update(extra)
    return data


@pytest.fixture()
def product_id(services: AppServices, category_id: int) -> int:
    """A saved product with 20 units of opening stock."""
    return services.products.create(_form(category_id, opening_quantity="20")).product.id


# -- product service ----------------------------------------------------------------
def test_create_books_opening_stock_as_transaction(
    services: AppServices, product_id: int, audit
) -> None:
    """Opening stock is a traceable stock-in, not a silent quantity."""
    product = services.products.get(product_id)
    history = services.stock.history(TransactionFilter(product_id=product_id), ListQuery())
    assert product.quantity_on_hand == 20 and history.total == 1
    assert history.items[0].reference_note == "Opening stock"
    assert [e.action for e in audit()] == ["CREATE", "CREATE", "STOCK_IN"]


def test_duplicate_sku_rejected(services: AppServices, category_id: int, product_id: int) -> None:
    """SKUs are unique (case-insensitive)."""
    with pytest.raises(ValidationError, match="already used"):
        services.products.create(_form(category_id, sku="sta-pen-001"))


def test_price_below_cost_is_a_warning(services: AppServices, category_id: int) -> None:
    """Selling below cost saves, but returns a warning."""
    result = services.products.create(_form(category_id, selling_price="5"))
    assert result.product.id and "below unit cost" in result.warnings[0]


@pytest.mark.parametrize(
    ("field", "value"),
    [("unit_cost", "-1"), ("reorder_level", "x"), ("unit", "tonne"), ("category_id", "")],
)
def test_invalid_product_fields(services: AppServices, category_id: int, field: str,
                                value: str) -> None:
    """Negative cost, non-numeric reorder level, unknown unit, no category."""
    data = _form(category_id)
    data[field] = value
    with pytest.raises(ValidationError):
        services.products.create(data)


def test_update_logs_changes_but_never_quantity(
    services: AppServices, category_id: int, product_id: int, audit
) -> None:
    """Edits are audited and cannot change stock on hand."""
    services.products.update(product_id, _form(category_id, name="Gel pen",
                                               quantity_on_hand="999"))
    assert services.products.get(product_id).quantity_on_hand == 20
    assert audit("UPDATE")[0].details["changes"] == {"name": {"old": "Ball pen", "new": "Gel pen"}}


def test_delete_with_history_is_soft(services: AppServices, product_id: int) -> None:
    """Products with transactions are deactivated, then can be restored."""
    assert services.products.delete(product_id) == "deactivated"
    assert services.products.find(ListQuery()).total == 0
    assert services.products.restore(product_id).is_active


def test_delete_without_history_is_hard(services: AppServices, category_id: int) -> None:
    """Products never moved are removed completely."""
    new_id = services.products.create(_form(category_id)).product.id
    assert services.products.delete(new_id) == "deleted"


def test_product_export_csv(services: AppServices, product_id: int, tmp_path: Path,
                            audit) -> None:
    """Export writes every active product and logs EXPORT."""
    path = services.products.export_csv(path=tmp_path / "p.csv")
    frame = pd.read_csv(path, encoding="utf-8-sig")
    assert frame.iloc[0]["SKU"] == "STA-PEN-001" and frame.iloc[0]["Stock value"] == 200
    assert audit("EXPORT")[0].details["rows"] == 1


# -- stock service ------------------------------------------------------------------
def test_stock_out_reduces_quantity_and_logs_old_new(
    services: AppServices, product_id: int, audit
) -> None:
    """A stock-out records the movement and old -> new quantity."""
    result = services.stock.stock_out(product_id, "8", note="Sale #12")
    assert result.product.quantity_on_hand == 12 and result.transaction.quantity == 8
    assert audit("STOCK_OUT")[0].details["quantity_on_hand"] == {"old": 20, "new": 12}


def test_stock_out_cannot_go_negative(services: AppServices, product_id: int, audit) -> None:
    """Over-issuing raises StockError and writes nothing."""
    with pytest.raises(StockError, match="only 20 in stock"):
        services.stock.stock_out(product_id, 21)
    assert services.products.get(product_id).quantity_on_hand == 20
    assert audit("STOCK_OUT") == []


def test_low_stock_alert_after_issue(services: AppServices, product_id: int) -> None:
    """Dropping to the reorder level flags the product as low stock."""
    assert services.stock.stock_out(product_id, 15).low_stock_alert
    assert services.products.low_stock_count() == 1


def test_adjust_to_counted_quantity(services: AppServices, product_id: int) -> None:
    """Adjustments store the signed delta and require a reason."""
    result = services.stock.adjust(product_id, "17", "Damaged in storage")
    assert result.transaction.quantity == -3 and result.product.quantity_on_hand == 17
    with pytest.raises(ValidationError, match="Reason"):
        services.stock.adjust(product_id, "10", "")
    with pytest.raises(ValidationError, match="nothing to adjust"):
        services.stock.adjust(product_id, "17", "Recount")


def test_stock_in_with_backdated_time(services: AppServices, product_id: int) -> None:
    """Imports/seeding may back-date movements."""
    when = datetime(2026, 1, 15, 9, 30)
    result = services.stock.stock_in(product_id, 5, unit_cost="9.5", occurred_at=when)
    assert result.transaction.created_at == "2026-01-15 09:30:00"
    assert result.transaction.unit_cost == 9.5 and result.product.quantity_on_hand == 25


def test_inactive_product_cannot_move(services: AppServices, product_id: int) -> None:
    """Deactivated products are frozen."""
    services.products.delete(product_id)
    with pytest.raises(StockError, match="deactivated"):
        services.stock.stock_in(product_id, 1)


def test_failed_audit_rolls_back_movement(
    services: AppServices, product_id: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the audit write fails, the stock change is rolled back too (atomicity)."""
    import services.stock_service as stock_module

    def broken_log(*args: object, **kwargs: object) -> None:
        raise RuntimeError("disk full")

    monkeypatch.setattr(stock_module, "log_activity", broken_log)
    with pytest.raises(RuntimeError):
        services.stock.stock_out(product_id, 5)
    assert services.products.get(product_id).quantity_on_hand == 20
    assert services.stock.history(TransactionFilter(tx_type="OUT"), ListQuery()).total == 0


def test_stock_export_csv(services: AppServices, product_id: int, tmp_path: Path) -> None:
    """Transaction history exports with a value column."""
    services.stock.stock_out(product_id, 2)
    frame = pd.read_csv(services.stock.export_csv(TransactionFilter(), tmp_path / "t.csv"),
                        encoding="utf-8-sig")
    assert list(frame["Type"]) == ["OUT", "IN"] and frame.iloc[0]["Value"] == 20
