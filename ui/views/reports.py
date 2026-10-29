"""Reports screen: inventory turnover, days of stock and the reorder list.

Turnover (COGS ÷ average inventory value) is the baseline TQM metric. Days of
stock flags products likely to stock out soon. Both reports export to CSV
for submission or further analysis. The tabs are implemented in
:mod:`ui.views.report_turnover` and :mod:`ui.views.report_reorder`.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import customtkinter as ctk

from models.reports import TurnoverRow
from ui.components.messages import show_info
from ui.views.base_view import BaseView
from ui.views.report_period import PeriodBar
from ui.views.report_reorder import ReorderPanel
from ui.views.report_turnover import TurnoverPanel
from utils.formatters import format_ratio


class ReportsView(BaseView):
    """Turnover and reorder reports with CSV export."""

    title = "Reports"
    subtitle = ("Inventory turnover = COGS ÷ average inventory value (daily average over the "
                "period). Days of stock = on hand ÷ average daily usage.")

    def build(self) -> None:
        """Period bar, summary line and the two report tabs."""
        cfg = self.services.config
        self.period_bar = PeriodBar(self.body, cfg.get("inventory.report_periods"), self.refresh)
        self.period_bar.pack(fill="x", pady=(0, 8))
        self.summary = ctk.CTkLabel(self.body, text="", font=self.theme.font(1), anchor="w")
        self.summary.pack(fill="x", pady=(0, 6))
        tabs = ctk.CTkTabview(self.body)
        tabs.pack(fill="both", expand=True)
        self.turnover = TurnoverPanel(tabs.add("Inventory turnover"), self.theme, self.money,
                                      cfg.get("inventory.days_of_stock_warning"),
                                      self._export_turnover)
        self.turnover.pack(fill="both", expand=True)
        self.reorder = ReorderPanel(tabs.add("Reorder list"), self.theme, self._export_low)
        self.reorder.pack(fill="both", expand=True)

    def on_show(self) -> None:
        """Preset the configured turnover period the first time, then run the reports."""
        if self.period_bar.is_empty():
            start, end = self.services.reports.default_period()
            self.period_bar.preset(start, end, self.setting("date_format"))
        super().on_show()

    def refresh(self) -> None:
        """Run the turnover report for the selected period and reload the reorder list.

        Errors (for example a mistyped date) are shown and logged by
        :meth:`BaseView.guarded`, and leave the previous results on screen.
        """
        period = self.guarded("Reports > Period", self._period)
        rows = period and self.guarded("Reports > Turnover",
                                       lambda: self.services.reports.turnover_report(*period))
        if period and rows is not None:
            self._show_summary(period, rows)
            self.turnover.show(rows)
        low = self.guarded("Reports > Reorder list", self.services.reports.low_stock)
        if low is not None:
            self.reorder.show(low)

    def _period(self) -> tuple[date, date]:
        """Validated period from the period bar (defaults to the configured window)."""
        return self.period_bar.read(self.setting("date_format"),
                                    self.services.reports.default_period())

    def _show_summary(self, period: tuple[date, date], rows: list[TurnoverRow]) -> None:
        """Store-wide summary line.

        Args:
            period: Report period.
            rows: Turnover rows for that period.
        """
        cogs = sum(r.cogs for r in rows)
        average = sum(r.average_inventory_value for r in rows)
        overall = cogs / average if average else 0.0
        fmt = self.setting("date_format")
        self.summary.configure(
            text=f"{period[0].strftime(fmt)} → {period[1].strftime(fmt)}   ·   "
                 f"Store turnover {format_ratio(overall)}   ·   COGS {self.money(cogs)}   ·   "
                 f"Avg inventory {self.money(average)}")

    def _export_turnover(self) -> None:
        """Export the turnover report for the selected period."""
        period = self.guarded("Reports > Period", self._period)
        if period is not None:
            self._exported(self.guarded("Reports > Export turnover",
                                        lambda: self.services.reports.export_turnover_csv(*period)))

    def _export_low(self) -> None:
        """Export the reorder list."""
        self._exported(self.guarded("Reports > Export reorder list",
                                    self.services.reports.export_low_stock_csv))

    def _exported(self, path: Path | None) -> None:
        """Tell the operator where an exported file was saved.

        Args:
            path: Written file, or ``None`` when the export failed.
        """
        if path:
            self.notify(f"Exported {path.name}", "success")
            show_info(self, "Export complete", f"Report saved to:\n{path}")
