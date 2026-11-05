"""One figure in a divided strip: a label, a number and a caption.

KPIs are type, not tiles: no icon, no sparkline and no tinted background. Cells
sit side by side in one container split by 1px dividers.

Layer: ui/components
Author: Siddhi Baluja
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ui.theme import Theme


class StatCard(ctk.CTkFrame):
    """A KPI cell.

    Args:
        master: Parent widget.
        theme: Shared theme.
        title: Label above the value.
        lead: The screen's answer figure, set larger and heavier than its siblings.
    """

    def __init__(self, master: Any, theme: Theme, title: str, lead: bool = False) -> None:
        super().__init__(master, fg_color="transparent")
        self._theme = theme
        ctk.CTkLabel(self, text=title, height=18, font=theme.font(-1), anchor="w",
                     text_color=theme.color("muted")).pack(fill="x")
        # 30px for the lead, 22px for its siblings.
        font = theme.font(16, "bold") if lead else theme.font(8)
        self._value = ctk.CTkLabel(self, text="–", height=38, anchor="w", font=font)
        self._value.pack(fill="x")
        self._caption = ctk.CTkLabel(self, text="", height=16, font=theme.font(-2), anchor="w",
                                     text_color=theme.color("muted"))
        self._caption.pack(fill="x")

    def set(self, value: str, caption: str = "", color: str = "text") -> None:
        """Update the displayed figure.

        Args:
            value: Formatted figure.
            caption: Small line under it.
            color: Palette name for the figure (``danger`` for a signal, ``muted`` for a zero).
        """
        self._value.configure(text=value, text_color=self._theme.color(color))
        self._caption.configure(text=caption)
