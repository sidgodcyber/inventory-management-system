"""Matplotlib chart embedded in CustomTkinter via ``FigureCanvasTkAgg``.

The panel owns one figure and redraws it through a callback, applying the
theme's light/dark chart colours so charts follow the appearance setting.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from ui.theme import Theme  # noqa: E402

DrawFunction = Callable[[Axes, Theme], None]


class ChartPanel(ctk.CTkFrame):
    """A titled frame holding one themed Matplotlib axes.

    Args:
        master: Parent widget.
        theme: Shared theme.
        title: Heading shown above the chart.
        dpi: Figure resolution (from config).
    """

    def __init__(self, master: Any, theme: Theme, title: str, dpi: int) -> None:
        super().__init__(master, corner_radius=10)
        self._theme = theme
        self._draw_callback: DrawFunction | None = None  # not "_draw": CTk uses that name
        self._grid_axis = "y"
        ctk.CTkLabel(self, text=title, font=theme.font(1, "bold"), anchor="w").pack(
            fill="x", padx=14, pady=(10, 0))
        self.figure = Figure(figsize=(5, 3), dpi=dpi)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        theme.on_change(self.redraw)

    def plot(self, draw: DrawFunction, grid_axis: str = "y") -> None:
        """Remember ``draw(ax, theme)`` and render it.

        Args:
            draw: Callback that plots onto the axes.
            grid_axis: ``"y"`` for column/line charts, ``"x"`` for horizontal bars.
        """
        self._draw_callback = draw
        self._grid_axis = grid_axis
        self.redraw()

    def redraw(self) -> None:
        """Clear the figure, re-run the draw callback and apply theme colours."""
        if self._draw_callback is None:
            return
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self._draw_callback(ax, self._theme)
        self._style(ax)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _style(self, ax: Axes) -> None:
        """Apply background, text and grid colours for the current mode."""
        background = self._theme.mode_color("chart_bg")
        foreground = self._theme.mode_color("chart_fg")
        self.figure.set_facecolor(self._theme.mode_color("card_bg"))  # blends into the card
        ax.set_facecolor(background)
        ax.tick_params(colors=foreground, labelsize=8)
        ax.xaxis.label.set_color(foreground)
        ax.yaxis.label.set_color(foreground)
        ax.title.set_color(foreground)
        for spine in ax.spines.values():
            spine.set_color(self._theme.mode_color("grid"))
        ax.grid(axis=self._grid_axis, color=self._theme.mode_color("grid"), linewidth=0.6)
        ax.set_axisbelow(True)
        legend = ax.get_legend()
        if legend is not None:
            legend.get_frame().set_facecolor(background)
            for text in legend.get_texts():
                text.set_color(foreground)

    def destroy(self) -> None:
        """Unregister from theme changes, then destroy the widget."""
        self._theme.remove_listener(self.redraw)
        super().destroy()
