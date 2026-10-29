"""Reports screen: inventory turnover, days of stock and the reorder list.

Turnover (COGS ÷ average inventory value) is the baseline TQM metric. Days of
stock flags products likely to stock out soon. Both reports export to CSV
for submission or further analysis.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from datetime import date
from typing import Any

import customtkinter as ctk

from models.product import Product
from models.reports import TurnoverRow
from ui.components.data_table import TAG_LOW, TAG_STOCKOUT, TAG_WARNING, Column, DataTable, Row
from ui.components.messages import show_info
from ui.views.base_view import BaseView
from utils.date_helpers import days_ago
from utils.formatters import format_days, format_number, format_ratio
from utils.validators import Validator

CUSTOM = "Custom"


class ReportsView(BaseView):
    """Turnover and low-stock reports with CSV export."""

    title = "Reports"
    subtitle = ("Inventory turnover = COGS ÷ average inventory value (daily average over the "
                "period). Days of stock = on hand ÷ average daily usage.")
    turnover_columns = (
        Column("sku", "SKU", 100),
        Column("name", "Product", 190),
        Column("category_name", "Category", 115),
        Column("quantity_on_hand", "On hand", 70, "e"),
        Column("units_sold", "Issued", 70, "e"),
        Column("cogs", "COGS", 100, "e"),
        Column("average_inventory_value", "Avg inventory", 110, "e"),
        Column("turnover", "Turnover", 80, "e"),
        Column("avg_daily_usage", "Usage/day", 80, "e"),
        Column("days_of_stock", "Days of stock", 100, "e"),
    )
    low_columns = (
        Column("sku", "SKU", 110, sortable=False),
        Column("name", "Product", 230, sortable=False),
        Column("category_name", "Category", 130, sortable=False),
        Column("supplier_name", "Supplier", 180, sortable=False),
        Column("quantity_on_hand", "On hand", 80, "e", sortable=False),
        Column("reorder_level", "Reorder level", 100, "e", sortable=False),
        Column("status", "Status", 90, "center", sortable=False),
    )

    def build(self) -> None:
        """Period bar, summary line and two report tabs."""
        self._rows: list[TurnoverRow] = []
        self._sort = ("turnover", True)
        self._build_period_bar()
        self.summary = ctk.CTkLabel(self.body, text="", font=self.theme.font(1), anchor="w")
        self.summary.pack(fill="x", pady=(0, 6))
        tabs = ctk.CTkTabview(self.body)
        tabs.pack(fill="both", expand=True)
        self._build_turnover_tab(tabs.add("Inventory turnover"))
        self._build_low_tab(tabs.add("Reorder list"))

    def _build_period_bar(self) -> None:
        """Quick period buttons plus custom from/to dates."""
        bar = ctk.CTkFrame(self.body, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))
        periods = [f"{days} days" for days in self.services.config.get("inventory.report_periods")]
        self.period = ctk.CTkSegmentedButton(bar, values=[*periods, CUSTOM],
                                             command=self._period_chosen)
        self.period.pack(side="left")
        self.date_from = ctk.CTkEntry(bar, width=130)
        self.date_from.pack(side="left", padx=(12, 0))
        self.date_to = ctk.CTkEntry(bar, width=130)
        self.date_to.pack(side="left", padx=(6, 0))
        ctk.CTkButton(bar, text="Run report", width=110, command=self.refresh).pack(
            side="left", padx=(8, 0))

    def _build_turnover_tab(self, tab: Any) -> None:
        """Turnover table and its export button."""
        ctk.CTkButton(tab, text="Export turnover CSV", width=160, fg_color="transparent",
                      border_width=1, text_color=("gray10", "gray90"),
                      command=self._export_turnover).pack(anchor="e", pady=(0, 6))
        self.turnover_table = DataTable(tab, self.theme, self.turnover_columns,
                                        on_sort=self._on_sort, height=10)
        self.turnover_table.pack(fill="both", expand=True)
        self.turnover_table.mark_sorted(*self._sort)

    def _build_low_tab(self, tab: Any) -> None:
        """Reorder table and its export button."""
        ctk.CTkButton(tab, text="Export reorder list CSV", width=180, fg_color="transparent",
                      border_width=1, text_color=("gray10", "gray90"),
                      command=self._export_low).pack(anchor="e", pady=(0, 6))
        self.low_table = DataTable(tab, self.theme, self.low_columns, height=10)
        self.low_table.pack(fill="both", expand=True)

    # -- period ---------------------------------------------------------------------------
    def _period_chosen(self, value: str) -> None:
        """Fill the date boxes for a quick period and run the report."""
        if value == CUSTOM:
            return
        days = int(value.split()[0])
        fmt = self.setting("date_format")
        self._set_dates(days_ago(days - 1).strftime(fmt), date.today().strftime(fmt))
        self.refresh()

    def _set_dates(self, start: str, end: str) -> None:
        """Replace the text of both date boxes."""
        for entry, value in ((self.date_from, start), (self.date_to, end)):
            entry.delete(0, "end")
            entry.insert(0, value)

    def _read_period(self) -> tuple[date, date]:
        """Validated period from the date boxes (defaults to the configured period)."""
        fmt = self.setting("date_format")
        default_start, default_end = self.services.reports.default_period()
        start = Validator.date(self.date_from.get(), "From date", fmt) or default_start
        end = Validator.date(self.date_to.get(), "To date", fmt) or default_end
        if start > end:
            start, end = end, start  # be forgiving: swap a reversed range
        return start, end

    # -- data -----------------------------------------------------------------------------
    def on_show(self) -> None:
        """Default to the configured turnover period the first time."""
        if not self.date_from.get():
            days = self.services.config.get("inventory.turnover_period_days")
            label = f"{days} days"
            self.period.set(label if label in self.period.cget("values") else CUSTOM)
            fmt = self.setting("date_format")
            start, end = self.services.reports.default_period()
            self._set_dates(start.strftime(fmt), end.strftime(fmt))
        super().on_show()

    def refresh(self) -> None:
        """Run both reports for the selected period."""
        period = self.guarded("Reports > Period", self._read_period)
        if period is None:
            return
        rows = self.guarded("Reports > Turnover",
                            lambda: self.services.reports.turnover_report(*period))
        overall = self.guarded("Reports > Turnover",
                               lambda: self.services.reports.overall_turnover(*period))
        if rows is not None and overall is not None:
            self._rows = rows
            self._show_summary(period, rows, overall)
            self._render_turnover()
        low = self.guarded("Reports > Reorder list", self.services.reports.low_stock)
        if low is not None:
            self.low_table.set_rows(_low_row(p) for p in low)

    def _show_summary(self, period: tuple[date, date], rows: list[TurnoverRow],
                      overall: float) -> None:
        """One-line store-wide summary above the tabs."""
        cogs = sum(r.cogs for r in rows)
        average = sum(r.average_inventory_value for r in rows)
        fmt = self.setting("date_format")
        self.summary.configure(
            text=f"{period[0].strftime(fmt)} → {period[1].strftime(fmt)}   ·   "
                 f"Store turnover {format_ratio(overall)}   ·   COGS {self.money(cogs)}   ·   "
                 f"Avg inventory {self.money(average)}")

    def _on_sort(self, key: str, descending: bool) -> None:
        """Sort the report rows in memory (the whole report is already loaded)."""
        self._sort = (key, descending)
        self._render_turnover()

    def _render_turnover(self) -> None:
        """Show rows in the current sort order (missing values last)."""
        key, descending = self._sort
        present = [r for r in self._rows if getattr(r, key) is not None]
        missing = [r for r in self._rows if getattr(r, key) is None]
        present.sort(key=lambda r: getattr(r, key), reverse=descending)
        self.turnover_table.set_rows(self._turnover_row(r) for r in [*present, *missing])

    def _turnover_row(self, row: TurnoverRow) -> Row:
        """Table row; products about to run out are highlighted."""
        warn_days = self.services.config.get("inventory.days_of_stock_warning")
        urgent = row.days_of_stock is not None and row.days_of_stock <= warn_days
        tags = (TAG_STOCKOUT,) if row.quantity_on_hand == 0 else (
            (TAG_WARNING,) if urgent else ())
        values = (row.sku, row.name, row.category_name, row.quantity_on_hand, row.units_sold,
                  self.money(row.cogs), self.money(row.average_inventory_value),
                  format_ratio(row.turnover), format_number(row.avg_daily_usage, 2),
                  format_days(row.days_of_stock))
        return str(row.product_id), values, tags

    # -- exports --------------------------------------------------------------------------
    def _export_turnover(self) -> None:
        """Export the turnover report for the selected period."""
        period = self.guarded("Reports > Period", self._read_period)
        if period is not None:
            self._finish_export(self.guarded(
                "Reports > Export turnover",
                lambda: self.services.reports.export_turnover_csv(*period)))

    def _export_low(self) -> None:
        """Export the reorder list."""
        self._finish_export(self.guarded("Reports > Export reorder list",
                                         self.services.reports.export_low_stock_csv))

    def _finish_export(self, path: Any) -> None:
        """Tell the operator where the file went."""
        if path:
            self.notify(f"Exported {path.name}", "success")
            show_info(self, "Export complete", f"Report saved to:\n{path}")


def _low_row(product: Product) -> Row:
    """Reorder list row."""
    tag = TAG_STOCKOUT if product.is_out_of_stock else TAG_LOW
    values = (product.sku, product.name, product.category_name, product.supplier_name or "—",
              product.quantity_on_hand, product.reorder_level, product.status)
    return str(product.id), values, (tag,)
