"""Inventory analytics: turnover rate, days of stock, dashboard figures.

Formulas (documented in docs/SRS.md, section CTQ):

* ``COGS``         = sum over OUT movements in the period of quantity x unit cost
* ``opening qty``  = current qty - net movement after the day before the period
* ``closing qty``  = current qty - net movement after the period end
* ``avg inventory`` = (opening qty + closing qty) / 2 x current unit cost
* ``turnover``     = COGS / average inventory value
* ``avg daily usage`` = units issued / days in period
* ``days of stock``   = quantity on hand / average daily usage

Layer: services
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from config.config_loader import AppConfig
from core.constants import ACTION_EXPORT, TX_IN, TX_OUT
from core.logger import log_activity
from models.product import Product
from models.reports import DashboardStats, TurnoverRow
from repositories.product_repository import ProductRepository
from repositories.stock_transaction_repository import StockTransactionRepository
from utils.csv_export import default_export_path, write_csv
from utils.date_helpers import date_range, days_ago, days_between, end_of_day, period_bounds

TURNOVER_COLUMNS: tuple[tuple[str, str], ...] = (
    ("sku", "SKU"),
    ("name", "Product"),
    ("category_name", "Category"),
    ("quantity_on_hand", "On hand"),
    ("units_sold", "Units issued"),
    ("cogs", "COGS"),
    ("average_inventory_value", "Avg inventory value"),
    ("turnover", "Turnover"),
    ("avg_daily_usage", "Avg daily usage"),
    ("days_of_stock", "Days of stock"),
)

LOW_STOCK_COLUMNS: tuple[tuple[str, str], ...] = (
    ("sku", "SKU"),
    ("name", "Product"),
    ("category_name", "Category"),
    ("supplier_name", "Supplier"),
    ("quantity_on_hand", "On hand"),
    ("reorder_level", "Reorder level"),
    ("shortfall", "Shortfall"),
)


class ReportService:
    """Turnover, low-stock and dashboard analytics.

    Args:
        products: Product repository.
        transactions: Stock transaction repository.
        config: Configuration (turnover period, chart window, export folder).
    """

    def __init__(self, products: ProductRepository, transactions: StockTransactionRepository,
                 config: AppConfig) -> None:
        self._products = products
        self._transactions = transactions
        self._config = config

    # -- periods ------------------------------------------------------------------
    def default_period(self, today: date | None = None) -> tuple[date, date]:
        """The configured turnover window ending today."""
        end = today or date.today()
        return days_ago(self._config.get("inventory.turnover_period_days") - 1, end), end

    # -- turnover -----------------------------------------------------------------
    def turnover_report(self, start: date, end: date) -> list[TurnoverRow]:
        """Per-product turnover and days of stock for ``start``..``end``.

        Args:
            start: First day of the period (inclusive).
            end: Last day of the period (inclusive).

        Returns:
            One row per active product, highest turnover first.
        """
        frame = self._turnover_frame(start, end)
        if frame.empty:
            return []
        frame = frame.sort_values(["turnover", "cogs"], ascending=False)
        return [TurnoverRow(**_clean_row(row)) for row in frame.to_dict("records")]

    def overall_turnover(self, start: date, end: date) -> float:
        """Inventory turnover for the whole store over the period."""
        frame = self._turnover_frame(start, end)
        average = frame["average_inventory_value"].sum() if not frame.empty else 0.0
        return round(float(frame["cogs"].sum() / average), 2) if average > 0 else 0.0

    def _turnover_frame(self, start: date, end: date) -> pd.DataFrame:
        """Build the per-product turnover table with pandas."""
        products = self._products.list_all(active_only=True)
        if not products:
            return pd.DataFrame()
        period_start, period_end = period_bounds(start, end)
        issues = self._transactions.issues_by_product(period_start, period_end)
        change_since_start = self._transactions.net_change_after(
            end_of_day(start - timedelta(days=1)))
        change_after_end = self._transactions.net_change_after(period_end)
        frame = pd.DataFrame([_product_record(p) for p in products])
        ids = frame["product_id"]
        frame["units_sold"] = ids.map(lambda i: issues.get(i, (0, 0.0))[0])
        frame["cogs"] = ids.map(lambda i: issues.get(i, (0, 0.0))[1])
        opening = frame["quantity_on_hand"] - ids.map(lambda i: change_since_start.get(i, 0))
        closing = frame["quantity_on_hand"] - ids.map(lambda i: change_after_end.get(i, 0))
        frame["average_inventory_value"] = (opening + closing) / 2 * frame["unit_cost"]
        avg = frame["average_inventory_value"]
        frame["turnover"] = (frame["cogs"] / avg.where(avg > 0)).fillna(0.0)
        frame["avg_daily_usage"] = frame["units_sold"] / days_between(start, end)
        usage = frame["avg_daily_usage"]
        frame["days_of_stock"] = frame["quantity_on_hand"] / usage.where(usage > 0)
        return frame.drop(columns=["unit_cost"])

    # -- dashboard ----------------------------------------------------------------
    def dashboard_stats(self, today: date | None = None) -> DashboardStats:
        """Headline numbers for the dashboard stat cards."""
        summary = self._products.stock_summary()
        start, end = self.default_period(today)
        return DashboardStats(
            total_products=int(summary["total_products"]),
            total_stock_value=float(summary["total_value"]),
            low_stock_count=int(summary["low_stock_count"]),
            stockout_count=int(summary["stockout_count"]),
            turnover=self.overall_turnover(start, end),
            period_days=days_between(start, end),
        )

    def value_by_category(self) -> list[tuple[str, float]]:
        """Stock value at cost per category, largest first."""
        return self._products.value_by_category()

    def daily_movements(self, today: date | None = None) -> pd.DataFrame:
        """Units in and out per day for the configured chart window.

        Returns:
            DataFrame indexed by date with integer columns ``IN`` and ``OUT``;
            days without movements are filled with 0.
        """
        end = today or date.today()
        start = days_ago(self._config.get("inventory.chart_days") - 1, end)
        totals = self._transactions.daily_totals(*period_bounds(start, end))
        frame = pd.DataFrame(totals, columns=["day", "type", "units"])
        table = frame.pivot_table(index="day", columns="type", values="units",
                                  aggfunc="sum", fill_value=0)
        table.index = pd.to_datetime(table.index).date
        days = date_range(start, end)
        return table.reindex(index=days, columns=[TX_IN, TX_OUT], fill_value=0).astype(int)

    def low_stock(self) -> list[Product]:
        """Products at or below reorder level, most urgent first."""
        return self._products.low_stock()

    # -- exports ------------------------------------------------------------------
    def export_turnover_csv(self, start: date, end: date, path: Path | None = None) -> Path:
        """Export the turnover report and log ``EXPORT``."""
        rows = [vars(row) for row in self.turnover_report(start, end)]
        target = path or self._export_path("turnover")
        write_csv(rows, TURNOVER_COLUMNS, target)
        log_activity(ACTION_EXPORT, "Report", "turnover",
                     {"file": str(target), "rows": len(rows),
                      "period": [start.isoformat(), end.isoformat()]})
        return target

    def export_low_stock_csv(self, path: Path | None = None) -> Path:
        """Export the low-stock (reorder) list and log ``EXPORT``."""
        rows = [{**p.to_dict(), "shortfall": p.reorder_level - p.quantity_on_hand}
                for p in self.low_stock()]
        target = path or self._export_path("low_stock")
        write_csv(rows, LOW_STOCK_COLUMNS, target)
        log_activity(ACTION_EXPORT, "Report", "low_stock", {"file": str(target), "rows": len(rows)})
        return target

    def _export_path(self, prefix: str) -> Path:
        """Timestamped path inside the configured export folder."""
        return default_export_path(self._config.resolve_path("paths.export_dir"), prefix)


def _product_record(product: Product) -> dict[str, object]:
    """The product columns the turnover table starts from."""
    return {
        "product_id": product.id,
        "sku": product.sku,
        "name": product.name,
        "category_name": product.category_name,
        "quantity_on_hand": product.quantity_on_hand,
        "unit_cost": product.unit_cost,
    }


def _clean_row(row: dict[str, object]) -> dict[str, object]:
    """Round money/ratios and turn NaN days-of-stock into ``None``."""
    days = row["days_of_stock"]
    return {
        **row,
        "product_id": int(row["product_id"]),
        "quantity_on_hand": int(row["quantity_on_hand"]),
        "units_sold": int(row["units_sold"]),
        "cogs": round(float(row["cogs"]), 2),
        "average_inventory_value": round(float(row["average_inventory_value"]), 2),
        "turnover": round(float(row["turnover"]), 2),
        "avg_daily_usage": round(float(row["avg_daily_usage"]), 2),
        "days_of_stock": None if pd.isna(days) else round(float(days), 1),
    }
