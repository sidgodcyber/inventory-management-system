"""Dashboard stat card: a title, a big number and a caption.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ui.theme import Theme


class StatCard(ctk.CTkFrame):
    """A compact KPI tile.

    Args:
        master: Parent widget.
        theme: Shared theme.
        title: Label above the value.
        accent: Palette colour name for the left accent strip.
    """

    def __init__(self, master: Any, theme: Theme, title: str, accent: str = "accent") -> None:
        super().__init__(master, corner_radius=10)
        self._theme = theme
        self._strip = ctk.CTkFrame(self, width=5, corner_radius=3,
                                   fg_color=theme.color(accent))
        self._strip.pack(side="left", fill="y", padx=(8, 0), pady=10)
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=12, pady=10)
        ctk.CTkLabel(body, text=title, font=theme.font(-1),
                     text_color=theme.color("muted"), anchor="w").pack(fill="x")
        self._value = ctk.CTkLabel(body, text="–", font=theme.font(10, "bold"), anchor="w")
        self._value.pack(fill="x")
        self._caption = ctk.CTkLabel(body, text="", font=theme.font(-2),
                                     text_color=theme.color("muted"), anchor="w")
        self._caption.pack(fill="x")

    def set(self, value: str, caption: str = "", accent: str | None = None) -> None:
        """Update the displayed value, caption and (optionally) accent colour."""
        self._value.configure(text=value)
        self._caption.configure(text=caption)
        if accent:
            self._strip.configure(fg_color=self._theme.color(accent))
