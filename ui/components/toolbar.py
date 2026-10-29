"""Toolbar with a debounced search box and action buttons.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ui.theme import Theme


class Toolbar(ctk.CTkFrame):
    """Search entry on the left, buttons on the right.

    Args:
        master: Parent widget.
        theme: Shared theme.
        on_search: Called with the search text after typing pauses
            (``None`` hides the search box).
        debounce_ms: Pause length before searching.
        placeholder: Hint text in the search box.
    """

    def __init__(self, master: Any, theme: Theme, on_search: Callable[[str], None] | None,
                 debounce_ms: int, placeholder: str = "Search…") -> None:
        super().__init__(master, fg_color="transparent")
        self._theme = theme
        self._on_search = on_search
        self._debounce_ms = debounce_ms
        self._job: str | None = None
        self.search = ctk.CTkEntry(self, width=280, placeholder_text=placeholder,
                                   font=theme.font())
        if on_search is not None:
            self.search.pack(side="left")
            self.search.bind("<KeyRelease>", self._schedule)
        self.left = ctk.CTkFrame(self, fg_color="transparent")
        self.left.pack(side="left", padx=(10, 0))

    def add_button(self, text: str, command: Callable[[], None], kind: str = "primary",
                   width: int = 110) -> ctk.CTkButton:
        """Add a right-aligned button.

        Args:
            text: Button label.
            command: Click handler.
            kind: ``primary``, ``secondary`` or ``danger``.
            width: Button width.

        Returns:
            The created button.
        """
        options: dict[str, Any] = {}
        if kind == "secondary":
            options = {"fg_color": "transparent", "border_width": 1,
                       "text_color": ("gray10", "gray90")}
        elif kind == "danger":
            options = {"fg_color": self._theme.color("danger")}
        button = ctk.CTkButton(self, text=text, width=width, command=command,
                               font=self._theme.font(), **options)
        button.pack(side="right", padx=(8, 0))
        return button

    @property
    def text(self) -> str:
        """Current search text."""
        return self.search.get().strip()

    def _schedule(self, _event: object) -> None:
        """Restart the debounce timer on every key press."""
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(self._debounce_ms, self._fire)

    def _fire(self) -> None:
        """Run the search callback."""
        self._job = None
        if self._on_search is not None:
            self._on_search(self.text)
