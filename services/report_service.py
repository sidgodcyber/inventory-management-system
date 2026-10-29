"""Inventory analytics: turnover rate, days of stock and dashboard figures.

This service gathers data from the repositories and hands it to the pure
calculations in :mod:`services.turnover` (formulas documented there and in
docs/SRS.md, section CTQ). Report exports are audited as ``EXPORT``.

Layer: services
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from config.config_loader import AppConfig
from core.constants import ACTION_EXPORT, TX_IN, TX_OUT
from core.logger import log_activity
from models.product import Product
from models.reports import DashboardStats, TurnoverRow
from repositories.product_repository import ProductRepository
from repositories.stock_transaction_repository import StockTransactionRepository
from services import turnover
from utils.csv_export import default_export_path, write_csv
from utils.date_helpers import date_range, days_ago, days_between, period_bounds

TURNOVER_COLUMNS: tuple[tuple[str, str], ...] = (
    ("sku", "SKU"), ("name", "Product"), ("category_name", "Category"),
    ("quantity_on_hand", "On hand"), ("units_sold", "Units issued"), ("cogs", "COGS"),
    ("average_inventory_value", "Avg inventory value"), ("turnover", "Turnover"),
    ("avg_daily_usage", "Avg daily usage"), ("days_of_stock", "Days of stock"),
)

LOW_STOCK_COLUMNS: tuple[tuple[str, str], ...] = (
    ("sku", "SKU"), ("name", "Product"), ("category_name", "Category"),
    ("supplier_name", "Supplier"), ("quantity_on_hand", "On hand"),
    ("reorder_level", "Reorder level"), ("shortfall", "Shortfall"),
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

    def default_period(self, today: date | None = None) -> tuple[date, date]:
        """The configured turnover window ending today.

        Args:
            today: Override for "today" (tests).

        Returns:
            ``(first day, last day)`` covering ``turnover_period_days`` days.
        """
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
        return turnover.to_rows(self._turnover_frame(start, end))

    def overall_turnover(self, start: date, end: date) -> float:
        """Inventory turnover for the whole store.

        Args:
            start: First day of the period (inclusive).
            end: Last day of the period (inclusive).

        Returns:
            Total COGS divided by total average inventory value.
        """
        return turnover.overall_turnover(self._turnover_frame(start, end))

    def _turnover_frame(self, start: date, end: date) -> pd.DataFrame:
        """Fetch inputs and build the per-product turnover table."""
        products = self._products.list_all(active_only=True)
        if not products:
            return pd.DataFrame()
        period_start, period_end = period_bounds(start, end)
        on_hand = pd.Series({p.id: p.quantity_on_hand for p in products})
        average_qty = turnover.average_daily_quantity(
            on_hand, self._transactions.daily_net_change(period_start, period_end),
            self._transactions.net_change_after(period_end), date_range(start, end))
        issues = self._transactions.issues_by_product(period_start, period_end)
        return turnover.turnover_table(products, issues, average_qty, days_between(start, end))

    # -- dashboard ----------------------------------------------------------------
    def dashboard_stats(self, today: date | None = None) -> DashboardStats:
        """Headline numbers for the dashboard stat cards.

        Args:
            today: Override for "today" (tests).

        Returns:
            Product count, stock value, low-stock and stockout counts, turnover.
        """
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
        """Stock value at cost per category.

        Returns:
            ``[(category, value), ...]`` largest first.
        """
        return self._products.value_by_category()

    def daily_movements(self, today: date | None = None) -> pd.DataFrame:
        """Units in and out per day for the configured chart window.

        Args:
            today: Override for "today" (tests).

        Returns:
            DataFrame indexed by date with integer columns ``IN`` and ``OUT``.
        """
        end = today or date.today()
        start = days_ago(self._config.get("inventory.chart_days") - 1, end)
        totals = self._transactions.daily_totals(*period_bounds(start, end))
        return turnover.daily_movement_table(totals, date_range(start, end), [TX_IN, TX_OUT])

    def low_stock(self) -> list[Product]:
        """Products that need reordering.

        Returns:
            Active products at or below reorder level, most urgent first.
        """
        return self._products.low_stock()

    # -- exports ------------------------------------------------------------------
    def export_turnover_csv(self, start: date, end: date, path: Path | None = None) -> Path:
        """Export the turnover report and log ``EXPORT``.

        Args:
            start: First day of the period.
            end: Last day of the period.
            path: Destination; defaults to a timestamped file in the export folder.

        Returns:
            The written file path.
        """
        rows = [vars(row) for row in self.turnover_report(start, end)]
        target = path or self._export_path("turnover")
        write_csv(rows, TURNOVER_COLUMNS, target)
        log_activity(ACTION_EXPORT, "Report", "turnover",
                     {"file": str(target), "rows": len(rows),
                      "period": [start.isoformat(), end.isoformat()]})
        return target

    def export_low_stock_csv(self, path: Path | None = None) -> Path:
        """Export the reorder list and log ``EXPORT``.

        Args:
            path: Destination; defaults to a timestamped file in the export folder.

        Returns:
            The written file path.
        """
        rows = [{**p.to_dict(), "shortfall": p.reorder_level - p.quantity_on_hand}
                for p in self.low_stock()]
        target = path or self._export_path("low_stock")
        write_csv(rows, LOW_STOCK_COLUMNS, target)
        log_activity(ACTION_EXPORT, "Report", "low_stock", {"file": str(target), "rows": len(rows)})
        return target

    def _export_path(self, prefix: str) -> Path:
        """Timestamped path inside the configured export folder."""
        return default_export_path(self._config.resolve_path("paths.export_dir"), prefix)
