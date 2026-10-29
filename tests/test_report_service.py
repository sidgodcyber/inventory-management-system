"""Tests for :mod:`services.report_service` using hand-calculated figures.

Scenario for product A (unit cost 10):

* 2026-01-01 IN 100, 2026-03-10 OUT 40, 2026-03-20 IN 20, so on hand = 80
* Period 1-31 Mar: daily closing stock is 100 for 9 days, 60 for 10, 80 for 12,
  avg qty = 2460 / 31 = 79.355, avg value 793.55, COGS 400, turnover 0.50
* Period 1-15 Mar: 100 for 9 days, 60 for 6, avg qty 84, avg value 840,
  COGS 400, turnover 0.48

Layer: tests
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from config.config_loader import AppConfig
from services.container import AppServices


def _create(services: AppServices, category_id: int, sku: str) -> int:
    """Create a product without opening stock."""
    form = {"sku": sku, "name": f"Item {sku}", "category_id": category_id, "unit": "pcs",
            "unit_cost": "10", "selling_price": "15", "reorder_level": "5"}
    return services.products.create(form).product.id


@pytest.fixture()
def scenario(services: AppServices) -> dict[str, int]:
    """Product A with the documented movements and product B with none."""
    category_id = services.categories.create("General").id
    a, b = _create(services, category_id, "A-1"), _create(services, category_id, "B-1")
    services.stock.stock_in(a, 100, occurred_at=datetime(2026, 1, 1, 9))
    services.stock.stock_out(a, 40, occurred_at=datetime(2026, 3, 10, 9))
    services.stock.stock_in(a, 20, occurred_at=datetime(2026, 3, 20, 9))
    return {"a": a, "b": b}


def test_turnover_full_month(services: AppServices, scenario: dict[str, int]) -> None:
    """Turnover, usage and days of stock match the hand calculation."""
    rows = {r.sku: r for r in services.reports.turnover_report(date(2026, 3, 1),
                                                                date(2026, 3, 31))}
    a = rows["A-1"]
    assert (a.units_sold, a.cogs, a.average_inventory_value) == (40, 400.0, 793.55)
    assert a.turnover == pytest.approx(0.5)
    assert a.avg_daily_usage == pytest.approx(1.29)
    assert a.days_of_stock == pytest.approx(62.0)


def test_turnover_partial_period_uses_closing_stock(
    services: AppServices, scenario: dict[str, int]
) -> None:
    """Movements after the period end are excluded from the closing stock."""
    a = services.reports.turnover_report(date(2026, 3, 1), date(2026, 3, 15))[0]
    assert a.sku == "A-1" and a.average_inventory_value == 840.0 and a.turnover == 0.48
    assert a.days_of_stock == pytest.approx(30.0)


def test_product_without_usage(services: AppServices, scenario: dict[str, int]) -> None:
    """No stock and no sales means turnover 0 and no days-of-stock estimate."""
    rows = {r.sku: r for r in services.reports.turnover_report(date(2026, 3, 1),
                                                                date(2026, 3, 31))}
    assert rows["B-1"].turnover == 0 and rows["B-1"].days_of_stock is None


def test_overall_turnover(services: AppServices, scenario: dict[str, int]) -> None:
    """Store-wide turnover = total COGS / total average inventory value."""
    assert services.reports.overall_turnover(date(2026, 3, 1), date(2026, 3, 31)) == 0.5


def test_empty_store_reports_zero(services: AppServices) -> None:
    """No products yields an empty report, not an exception."""
    assert services.reports.turnover_report(date(2026, 1, 1), date(2026, 1, 31)) == []
    assert services.reports.overall_turnover(date(2026, 1, 1), date(2026, 1, 31)) == 0.0


def test_daily_movements_fill_missing_days(
    services: AppServices, scenario: dict[str, int], config: AppConfig
) -> None:
    """The chart series covers every day of the window with zeros filled in."""
    frame = services.reports.daily_movements(today=date(2026, 3, 20))
    assert len(frame) == config.get("inventory.chart_days")
    assert frame.loc[date(2026, 3, 10), "OUT"] == 40
    assert frame.loc[date(2026, 3, 20), "IN"] == 20
    assert frame["IN"].sum() == 20


def test_dashboard_stats(services: AppServices, scenario: dict[str, int]) -> None:
    """Stat cards: 2 products, value 800, one stockout (B) counted as low too."""
    stats = services.reports.dashboard_stats(today=date(2026, 3, 31))
    assert (stats.total_products, stats.total_stock_value) == (2, 800.0)
    assert (stats.low_stock_count, stats.stockout_count) == (1, 1)
    assert stats.period_days == 90


def test_report_exports(services: AppServices, scenario: dict[str, int], tmp_path: Path,
                        audit) -> None:
    """Turnover and low-stock reports export to CSV and are audited."""
    turnover = services.reports.export_turnover_csv(date(2026, 3, 1), date(2026, 3, 31),
                                                    tmp_path / "t.csv")
    low = services.reports.export_low_stock_csv(tmp_path / "l.csv")
    assert pd.read_csv(turnover, encoding="utf-8-sig").iloc[0]["Turnover"] == 0.5
    assert pd.read_csv(low, encoding="utf-8-sig").iloc[0]["Shortfall"] == 5
    assert len(audit("EXPORT")) == 2
