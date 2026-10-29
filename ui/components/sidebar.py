"""Sidebar with the app name, one button per screen and a count badge.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ui.theme import Theme

_IDLE_TEXT = ("gray15", "gray85")
_ACTIVE_TEXT = ("white", "white")


class Sidebar(ctk.CTkFrame):
    """Vertical navigation panel.

    Args:
        master: Main window.
        theme: Shared theme.
        title: Short application name shown at the top.
        caption: Small text under the title.
        width: Sidebar width in pixels (from config).
        entries: ``(screen key, label)`` pairs in display order.
        on_select: Called with the screen key when a button is clicked.
    """

    def __init__(self, master: Any, theme: Theme, title: str, caption: str, width: int,
                 entries: Sequence[tuple[str, str]], on_select: Callable[[str], None]) -> None:
        super().__init__(master, width=width, corner_radius=0)
        self._theme = theme
        self.grid_propagate(False)
        ctk.CTkLabel(self, text=title, font=theme.font(12, "bold")).pack(pady=(24, 0))
        ctk.CTkLabel(self, text=caption, font=theme.font(-2),
                     text_color=theme.color("muted")).pack(pady=(0, 20))
        self._buttons = {key: self._button(key, label, on_select) for key, label in entries}
        self._badge: ctk.CTkLabel | None = None

    def _button(self, key: str, label: str, on_select: Callable[[str], None]) -> ctk.CTkButton:
        """One flat navigation button."""
        button = ctk.CTkButton(self, text=label, anchor="w", height=36, corner_radius=8,
                               fg_color="transparent", text_color=_IDLE_TEXT,
                               hover_color=("gray80", "gray25"), font=self._theme.font(1),
                               command=lambda: on_select(key))
        button.pack(fill="x", padx=12, pady=2)
        return button

    def highlight(self, key: str) -> None:
        """Mark the button of the visible screen as active.

        Args:
            key: Screen key currently shown.
        """
        for name, button in self._buttons.items():
            active = name == key
            button.configure(fg_color=self._theme.color("accent") if active else "transparent",
                             text_color=_ACTIVE_TEXT if active else _IDLE_TEXT)

    def set_badge(self, key: str, count: int) -> None:
        """Show ``count`` in a red badge on a button (hidden when zero).

        Args:
            key: Screen key whose button gets the badge.
            count: Number to display.
        """
        if self._badge is None:
            self._badge = ctk.CTkLabel(self._buttons[key], text="", width=26, height=20,
                                       corner_radius=10, fg_color=self._theme.color("danger"),
                                       text_color=self._theme.color("badge_fg"),
                                       font=self._theme.font(-2, "bold"))
        if count:
            self._badge.configure(text=str(count))
            self._badge.place(relx=1.0, rely=0.5, x=-10, anchor="e")
        else:
            self._badge.place_forget()
