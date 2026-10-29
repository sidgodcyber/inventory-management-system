"""Dashboard: headline stock health, two charts and the reorder list.

Supports the baseline TQM goal at a glance: how many products are at risk of
stockout, how fast inventory turns, where the money sits, and how stock has
moved over the last month. Cards and chart drawing live in
:mod:`ui.views.dashboard_cards` and :mod:`ui.views.dashboard_charts`.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import customtkinter as ctk

from models.product import Product
from ui.components.chart_panel import ChartPanel
from ui.components.data_table import TAG_LOW, TAG_STOCKOUT, Column, DataTable, Row
from ui.views.base_view import BaseView
from ui.views.dashboard_cards import KpiCards
from ui.views.dashboard_charts import draw_flow_lines, draw_value_bars

REORDER_COLUMNS = (
    Column("sku", "SKU", 110, sortable=False), Column("name", "Product", 240, sortable=False),
    Column("supplier_name", "Supplier", 180, sortable=False),
    Column("quantity_on_hand", "On hand", 80, "e", sortable=False),
    Column("reorder_level", "Reorder level", 100, "e", sortable=False),
    Column("shortfall", "Order at least", 110, "e", sortable=False),
    Column("status", "Status", 90, "center", sortable=False),
)


class DashboardView(BaseView):
    """KPI cards, charts and products needing reorder."""

    title = "Dashboard"
    subtitle = "Stock health at a glance: eliminate stockouts and keep inventory turning."

    def build(self) -> None:
        """Cards row, fixed-height charts row and the reorder table."""
        cfg = self.services.config
        self.cards = KpiCards(self.body, self.theme)
        self.cards.pack(fill="x")
        charts = ctk.CTkFrame(self.body, fg_color="transparent", height=cfg.get("ui.chart_height"))
        charts.pack(fill="x", pady=(12, 12))
        charts.pack_propagate(False)  # fixed height; the reorder list takes the rest
        self.value_chart = ChartPanel(charts, self.theme, "Stock value by category",
                                      cfg.get("ui.chart_dpi"))
        self.value_chart.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.flow_chart = ChartPanel(charts, self.theme,
                                     f"Units in vs out: last {cfg.get('inventory.chart_days')} days",
                                     cfg.get("ui.chart_dpi"))
        self.flow_chart.pack(side="left", fill="both", expand=True, padx=(6, 0))
        self._build_reorder_list()

    def _build_reorder_list(self) -> None:
        """Heading with a shortcut to Products, then the reorder table."""
        header = ctk.CTkFrame(self.body, fg_color="transparent")
        header.pack(fill="x", pady=(0, 6))
        self.reorder_title = ctk.CTkLabel(header, text="Needs reordering",
                                          font=self.theme.font(2, "bold"))
        self.reorder_title.pack(side="left")
        ctk.CTkButton(header, text="Open in Products", width=140, command=self._open_low_stock,
                      **self.theme.button_style("secondary")).pack(side="right")
        self.reorder_table = DataTable(self.body, self.theme, REORDER_COLUMNS, height=4)
        self.reorder_table.pack(fill="both", expand=True)

    def refresh(self) -> None:
        """Recompute every figure and chart from the report service.

        Each part loads independently through :meth:`BaseView.guarded`, so one
        failing query (logged as ``ERROR``) never blanks the whole dashboard.
        """
        reports = self.services.reports
        stats = self.guarded("Dashboard > Stats", reports.dashboard_stats)
        if stats is not None:
            self.cards.show(stats, self.money)
        by_category = self.guarded("Dashboard > Value chart", reports.value_by_category)
        if by_category is not None:
            self.value_chart.plot(
                lambda ax, theme: draw_value_bars(ax, theme, by_category, self.money), "x")
        flows = self.guarded("Dashboard > Movement chart", reports.daily_movements)
        if flows is not None:
            self.flow_chart.plot(lambda ax, theme: draw_flow_lines(ax, theme, flows))
        low = self.guarded("Dashboard > Reorder list", reports.low_stock)
        if low is not None:
            self.reorder_title.configure(text=f"Needs reordering ({len(low)})")
            self.reorder_table.set_rows(_reorder_row(p) for p in low)

    def _open_low_stock(self) -> None:
        """Jump to Products with the low-stock filter switched on."""
        self.app.view("products").show_low_stock()
        self.app.show("products")


def _reorder_row(product: Product) -> Row:
    """Reorder row with the minimum order that lifts stock above the reorder level."""
    shortfall = product.reorder_level - product.quantity_on_hand + 1
    tag = TAG_STOCKOUT if product.is_out_of_stock else TAG_LOW
    values = (product.sku, product.name, product.supplier_name or "—",
              product.quantity_on_hand, product.reorder_level, shortfall, product.status)
    return str(product.id), values, (tag,)
