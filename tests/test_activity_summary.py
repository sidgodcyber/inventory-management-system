"""Tests for the Activity Log one-line summary presenter.

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from ui.views.activity_summary import summarize


def test_update_changes_summary() -> None:
    """UPDATE payloads read as field: old → new."""
    assert summarize({"changes": {"name": {"old": "Pen", "new": "Gel pen"}}}) == \
        "name: Pen → Gel pen"


def test_stock_movement_summary() -> None:
    """Stock payloads show SKU, quantity and on-hand change."""
    text = summarize({"sku": "A-1", "quantity": 5, "note": "Sale",
                      "quantity_on_hand": {"old": 10, "new": 5}})
    assert text == "A-1 qty 5: 10 → 5  Sale"


def test_settings_and_error_summaries() -> None:
    """Settings show old → new; errors show context, type and message."""
    assert summarize({"old": 15, "new": 25}) == "15 → 25"
    assert summarize({"context": "Stock > Stock out", "type": "StockError",
                      "message": "only 2"}) == "[Stock > Stock out] StockError: only 2"


def test_generic_summary() -> None:
    """Anything else is rendered as key=value pairs."""
    assert summarize({"file": "a.csv", "rows": 3}) == "file=a.csv, rows=3"
