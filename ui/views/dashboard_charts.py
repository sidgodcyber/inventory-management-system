"""Drawing functions for the dashboard's two Matplotlib charts.

Each function draws onto the axes handed in by
:class:`~ui.components.chart_panel.ChartPanel`, which applies the theme colours
afterwards. Series colours come from the validated categorical pair in the
palette (``chart_series1`` / ``chart_series2``), never from status colours.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd
from matplotlib.axes import Axes
from matplotlib.dates import DateFormatter
from matplotlib.ticker import FuncFormatter

from core.constants import TX_IN, TX_OUT
from ui.theme import Theme


def draw_value_bars(ax: Axes, theme: Theme, data: list[tuple[str, float]],
                    money: Callable[[float], str]) -> None:
    """Horizontal bars of stock value per category, largest at the top.

    Args:
        ax: Target axes.
        theme: Shared theme (series and text colours).
        data: ``[(category, value), ...]`` largest first.
        money: Formats the value label at each bar end.
    """
    if not data:
        draw_empty(ax, theme)
        return
    names = [name for name, _ in reversed(data)]
    values = [value for _, value in reversed(data)]
    bars = ax.barh(names, values, height=0.6, color=theme.mode_color("chart_series1"))
    ax.bar_label(bars, labels=[money(v) for v in values], padding=4, fontsize=8,
                 color=theme.mode_color("chart_fg"))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: compact_number(v)))
    ax.set_xlim(0, max(values) * 1.3)  # room for the value labels
    ax.tick_params(axis="y", length=0)


def draw_flow_lines(ax: Axes, theme: Theme, frame: pd.DataFrame) -> None:
    """Two 2 px lines: units received and issued per day, legend above the plot.

    Args:
        ax: Target axes.
        theme: Shared theme (series colours).
        frame: Daily totals indexed by date with ``IN`` and ``OUT`` columns.
    """
    days = [pd.Timestamp(day) for day in frame.index]
    ax.plot(days, frame[TX_IN], color=theme.mode_color("chart_series1"), linewidth=2,
            label="Stock in")
    ax.plot(days, frame[TX_OUT], color=theme.mode_color("chart_series2"), linewidth=2,
            label="Stock out")
    ax.xaxis.set_major_formatter(DateFormatter("%d %b"))
    ax.set_ylabel("Units", fontsize=8)
    ax.set_ylim(bottom=0)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=8, frameon=False)


def draw_empty(ax: Axes, theme: Theme) -> None:
    """Placeholder text when there is nothing to plot.

    Args:
        ax: Target axes.
        theme: Shared theme (text colour).
    """
    ax.text(0.5, 0.5, "No data yet", ha="center", va="center", transform=ax.transAxes,
            color=theme.mode_color("chart_fg"))
    ax.set_xticks([])
    ax.set_yticks([])


def compact_number(value: float) -> str:
    """Short axis label.

    Args:
        value: Tick value.

    Returns:
        Text such as ``850``, ``12k`` or ``1.2M``.
    """
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    return f"{value / 1_000:.0f}k" if value >= 1_000 else f"{value:.0f}"
