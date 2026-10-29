"""Status bar with transient toast messages and permanent session info.

The left side shows short-lived feedback ("Product saved", warnings). The
right side shows operator name and role, database path and app version, all
taken from config/settings by the caller.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ui.theme import Theme

# Toast kinds mapped to palette colour names.
_KIND_COLORS = {"success": "success", "warning": "warning", "error": "danger", "info": "accent"}


class StatusBar(ctk.CTkFrame):
    """Bottom bar: toast on the left, session info on the right.

    Args:
        master: Parent widget.
        theme: Shared theme.
        toast_ms: How long toast messages stay visible.
    """

    def __init__(self, master: Any, theme: Theme, toast_ms: int) -> None:
        super().__init__(master, height=30, corner_radius=0)
        self._theme = theme
        self._toast_ms = toast_ms
        self._job: str | None = None
        self._message = ctk.CTkLabel(self, text="", anchor="w", font=theme.font(-1))
        self._message.pack(side="left", padx=12)
        self._info = ctk.CTkLabel(self, text="", anchor="e", font=theme.font(-1),
                                  text_color=theme.color("muted"))
        self._info.pack(side="right", padx=12)

    def set_info(self, text: str) -> None:
        """Replace the permanent right-hand text."""
        self._info.configure(text=text)

    def show(self, text: str, kind: str = "info") -> None:
        """Display a toast message that clears itself after ``toast_ms``.

        Args:
            text: Message to show.
            kind: ``info``, ``success``, ``warning`` or ``error``.
        """
        color = self._theme.color(_KIND_COLORS.get(kind, "accent"))
        self._message.configure(text=f"●  {text}", text_color=color)
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(self._toast_ms, self._clear)

    def _clear(self) -> None:
        """Remove the toast."""
        self._message.configure(text="")
        self._job = None
