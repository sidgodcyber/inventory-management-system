"""Dashboard: what is about to run out, and what to reorder today.

The screen answers that question first. The title row states the finding and
carries the main job, the headline figures lead with the reorder count, and the
stock runway is the largest block. The two charts beside it show how stock has
moved and where the money sits. Each part lives in its own module.

Layer: ui/views
Author: Siddhi Baluja
"""

from __future__ import annotations

import customtkinter as ctk

from models.reports import DashboardStats
from ui.components.chart_panel import ChartPanel
from ui.views.base_view import BaseView
from ui.views.dashboard_cards import KpiCards
from ui.views.dashboard_charts import draw_flow_lines, draw_value_bars
from ui.views.dashboard_runway import StockRunway


def finding(stats: DashboardStats) -> str:
    """The one sentence the screen leads with.

    Args:
        stats: Figures from the report service.

    Returns:
        What needs attention today, in words.
    """
    low = stats.low_stock_count - stats.stockout_count
    if not stats.low_stock_count:
        return "Every product is above its reorder level."
    if not stats.stockout_count:
        return f"{low} products are at or below their reorder level."
    return (f"{stats.stockout_count} products are out of stock and {low} more are at or below "
            "their reorder level.")


class DashboardView(BaseView):
    """Headline figures, the stock runway and two charts."""

    title = "Dashboard"
    subtitle = " "

    def build(self) -> None:
        """Title action, figures, then the runway beside the charts."""
        cfg = self.services.config
        ctk.CTkButton(self.header_actions, text="Review reorder list", width=150,
                      height=self.theme.control_height, command=self._open_low_stock).pack()
        self.cards = KpiCards(self.body, self.theme)
        self.cards.pack(fill="x")
        columns = ctk.CTkFrame(self.body, fg_color="transparent")
        columns.pack(fill="both", expand=True, pady=(12, 0))
        columns.grid_columnconfigure(0, weight=3, uniform="dash")
        columns.grid_columnconfigure(1, weight=2, uniform="dash")
        columns.grid_rowconfigure((0, 1), weight=1, uniform="charts")
        self.runway = StockRunway(columns, self.theme, cfg.get("ui.dashboard_reorder_rows"),
                                  self._open_low_stock)
        self.runway.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 12))
        days = cfg.get("inventory.chart_days")
        self.flow_chart = ChartPanel(columns, self.theme, f"Units in and out, last {days} days",
                                     cfg.get("ui.chart_dpi"))
        self.flow_chart.grid(row=0, column=1, sticky="nsew", pady=(0, 6))
        self.value_chart = ChartPanel(columns, self.theme, "Stock value by category",
                                      cfg.get("ui.chart_dpi"))
        self.value_chart.grid(row=1, column=1, sticky="nsew", pady=(6, 0))

    def refresh(self) -> None:
        """Recompute every figure and chart from the report service.

        Each part loads independently through :meth:`BaseView.guarded`, so one
        failing query (logged as ``ERROR``) never blanks the whole dashboard.
        """
        reports = self.services.reports
        stats = self.guarded("Dashboard > Stats", reports.dashboard_stats)
        if stats is not None:
            self.cards.show(stats, self.money)
            self.set_subtitle(finding(stats))
        low = self.guarded("Dashboard > Stock runway", reports.low_stock)
        days = self.guarded("Dashboard > Stock runway", reports.days_of_stock)
        active = self.guarded("Dashboard > Stock runway", self.services.products.list_active)
        if low is not None and days is not None and active is not None:
            self.runway.show(low, active, days)
        flows = self.guarded("Dashboard > Movement chart", reports.daily_movements)
        if flows is not None:
            self.flow_chart.plot(lambda ax, theme: draw_flow_lines(ax, theme, flows))
        by_category = self.guarded("Dashboard > Value chart", reports.value_by_category)
        if by_category is not None:
            self.value_chart.plot(
                lambda ax, theme: draw_value_bars(ax, theme, by_category, self.money), "x")

    def _open_low_stock(self) -> None:
        """Jump to Products with the low-stock filter switched on."""
        self.app.view("products").show_low_stock()
        self.app.show("products")
