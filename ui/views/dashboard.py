"""Dashboard: headline stock health, two charts and the reorder list.

Supports the baseline TQM goal at a glance: how many products are at risk of
stockout, how fast inventory turns, where the money sits, and how stock has
moved over the last month.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import customtkinter as ctk
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.dates import DateFormatter
from matplotlib.ticker import FuncFormatter

from core.constants import TX_IN, TX_OUT
from models.product import Product
from models.reports import DashboardStats
from ui.components.chart_panel import ChartPanel
from ui.components.data_table import TAG_LOW, TAG_STOCKOUT, Column, DataTable, Row
from ui.components.stat_card import StatCard
from ui.theme import Theme
from ui.views.base_view import BaseView
from utils.formatters import format_ratio


class DashboardView(BaseView):
    """Stat cards, charts and products needing reorder."""

    title = "Dashboard"
    subtitle = "Stock health at a glance: eliminate stockouts and keep inventory turning."
    reorder_columns = (
        Column("sku", "SKU", 110, sortable=False),
        Column("name", "Product", 240, sortable=False),
        Column("supplier_name", "Supplier", 180, sortable=False),
        Column("quantity_on_hand", "On hand", 80, "e", sortable=False),
        Column("reorder_level", "Reorder level", 100, "e", sortable=False),
        Column("shortfall", "Order at least", 110, "e", sortable=False),
        Column("status", "Status", 90, "center", sortable=False),
    )

    def build(self) -> None:
        """Cards row, charts row and reorder table."""
        self._build_cards()
        charts = ctk.CTkFrame(self.body, fg_color="transparent",
                              height=self.services.config.get("ui.chart_height"))
        charts.pack(fill="x", pady=(12, 12))
        charts.pack_propagate(False)  # fixed height; the reorder list takes the rest
        dpi = self.services.config.get("ui.chart_dpi")
        self.value_chart = ChartPanel(charts, self.theme, "Stock value by category", dpi)
        self.value_chart.pack(side="left", fill="both", expand=True, padx=(0, 6))
        days = self.services.config.get("inventory.chart_days")
        self.flow_chart = ChartPanel(charts, self.theme, f"Units in vs out: last {days} days", dpi)
        self.flow_chart.pack(side="left", fill="both", expand=True, padx=(6, 0))
        self._build_reorder_list()

    def _build_cards(self) -> None:
        """Five KPI tiles."""
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x")
        row.grid_columnconfigure(tuple(range(5)), weight=1, uniform="cards")
        specs = (("products", "Active products", "accent"),
                 ("value", "Stock value (at cost)", "accent"),
                 ("low", "Low stock", "warning"),
                 ("stockouts", "Stockouts", "danger"),
                 ("turnover", "Inventory turnover", "success"))
        self.cards: dict[str, StatCard] = {}
        for column, (key, title, accent) in enumerate(specs):
            card = StatCard(row, self.theme, title, accent)
            card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0))
            self.cards[key] = card

    def _build_reorder_list(self) -> None:
        """Products at or below their reorder level."""
        header = ctk.CTkFrame(self.body, fg_color="transparent")
        header.pack(fill="x", pady=(0, 6))
        self.reorder_title = ctk.CTkLabel(header, text="Needs reordering",
                                          font=self.theme.font(2, "bold"))
        self.reorder_title.pack(side="left")
        ctk.CTkButton(header, text="Open in Products", width=140, fg_color="transparent",
                      border_width=1, text_color=("gray10", "gray90"),
                      command=self._open_low_stock).pack(side="right")
        self.reorder_table = DataTable(self.body, self.theme, self.reorder_columns, height=4)
        self.reorder_table.pack(fill="both", expand=True)

    # -- data ---------------------------------------------------------------------------
    def refresh(self) -> None:
        """Recompute every figure from the services."""
        stats = self.guarded("Dashboard > Stats", self.services.reports.dashboard_stats)
        if stats is not None:
            self._show_stats(stats)
        by_category = self.guarded("Dashboard > Value chart",
                                   self.services.reports.value_by_category)
        if by_category is not None:
            self.value_chart.plot(lambda ax, theme: self._draw_values(ax, theme, by_category),
                                  grid_axis="x")
        flows = self.guarded("Dashboard > Movement chart", self.services.reports.daily_movements)
        if flows is not None:
            self.flow_chart.plot(lambda ax, theme: _draw_flows(ax, theme, flows))
        low = self.guarded("Dashboard > Reorder list", self.services.reports.low_stock)
        if low is not None:
            self.reorder_title.configure(text=f"Needs reordering ({len(low)})")
            self.reorder_table.set_rows(_reorder_row(p) for p in low)

    def _show_stats(self, stats: DashboardStats) -> None:
        """Fill the KPI tiles."""
        self.cards["products"].set(str(stats.total_products), "SKUs currently stocked")
        self.cards["value"].set(self.money(stats.total_stock_value), "quantity × unit cost")
        self.cards["low"].set(str(stats.low_stock_count), "at or below reorder level",
                              "warning" if stats.low_stock_count else "success")
        self.cards["stockouts"].set(str(stats.stockout_count), "products with zero stock",
                                    "danger" if stats.stockout_count else "success")
        self.cards["turnover"].set(format_ratio(stats.turnover),
                                   f"COGS ÷ avg inventory · {stats.period_days} days")

    def _draw_values(self, ax: Axes, theme: Theme, data: list[tuple[str, float]]) -> None:
        """Horizontal bars, largest at the top, value label at each bar end."""
        if not data:
            _empty(ax, theme)
            return
        names = [name for name, _ in reversed(data)]
        values = [value for _, value in reversed(data)]
        color = theme.mode_color("chart_series1")
        bars = ax.barh(names, values, height=0.6, color=color)
        ax.bar_label(bars, labels=[self.money(v) for v in values], padding=4, fontsize=8,
                     color=theme.mode_color("chart_fg"))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: _compact(v)))
        ax.set_xlim(0, max(values) * 1.3)
        ax.tick_params(axis="y", length=0)

    def _open_low_stock(self) -> None:
        """Jump to Products with the low-stock filter on."""
        self.app.show("products")
        products_view = self.app._views["products"]
        products_view.show_low_stock()
        products_view.refresh()


def _draw_flows(ax: Axes, theme: Theme, frame: pd.DataFrame) -> None:
    """Two 2px lines (units in and out per day) with a legend."""
    days = [pd.Timestamp(day) for day in frame.index]
    ax.plot(days, frame[TX_IN], color=theme.mode_color("chart_series1"), linewidth=2,
            label="Stock in")
    ax.plot(days, frame[TX_OUT], color=theme.mode_color("chart_series2"), linewidth=2,
            label="Stock out")
    ax.xaxis.set_major_formatter(DateFormatter("%d %b"))
    ax.set_ylabel("Units", fontsize=8)
    ax.set_ylim(bottom=0)
    # Legend above the plot area so it never covers the lines.
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=8, frameon=False)


def _empty(ax: Axes, theme: Theme) -> None:
    """Placeholder text when there is nothing to plot."""
    ax.text(0.5, 0.5, "No data yet", ha="center", va="center", transform=ax.transAxes,
            color=theme.mode_color("chart_fg"))
    ax.set_xticks([])
    ax.set_yticks([])


def _compact(value: float) -> str:
    """Axis label such as 12k or 1.2M."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    return f"{value / 1_000:.0f}k" if value >= 1_000 else f"{value:.0f}"


def _reorder_row(product: Product) -> Row:
    """Reorder table row with the minimum order that lifts stock above reorder level."""
    shortfall = product.reorder_level - product.quantity_on_hand + 1
    tag = TAG_STOCKOUT if product.is_out_of_stock else TAG_LOW
    values = (product.sku, product.name, product.supplier_name or "—",
              product.quantity_on_hand, product.reorder_level, shortfall, product.status)
    return str(product.id), values, (tag,)

