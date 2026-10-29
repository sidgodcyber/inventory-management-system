"""Pager: "Rows x–y of n · Page p of q" with previous/next buttons.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from models.common import Page
from ui.theme import Theme


class Pager(ctk.CTkFrame):
    """Pagination controls shown under a table.

    Args:
        master: Parent widget.
        theme: Shared theme.
        on_page: Called with the requested page number.
    """

    def __init__(self, master: Any, theme: Theme, on_page: Callable[[int], None]) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_page = on_page
        self._page = 1
        self._info = ctk.CTkLabel(self, text="", font=theme.font(-1))
        self._info.pack(side="left", padx=4)
        self._next = ctk.CTkButton(self, text="Next ›", width=80,
                                   command=lambda: self._on_page(self._page + 1))
        self._next.pack(side="right", padx=(6, 0))
        self._prev = ctk.CTkButton(self, text="‹ Prev", width=80,
                                   command=lambda: self._on_page(self._page - 1))
        self._prev.pack(side="right")

    def update_page(self, page: Page[Any]) -> None:
        """Show the position of ``page`` and enable the possible moves.

        Args:
            page: The page currently displayed.
        """
        self._page = page.page
        first = 0 if page.total == 0 else (page.page - 1) * page.page_size + 1
        last = min(page.page * page.page_size, page.total)
        self._info.configure(
            text=f"Rows {first}–{last} of {page.total}   ·   Page {page.page} of {page.pages}")
        self._prev.configure(state="normal" if page.has_previous else "disabled")
        self._next.configure(state="normal" if page.has_next else "disabled")
