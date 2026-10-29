"""Reusable data table: ttk.Treeview + scrollbar + clickable sort + pager.

CustomTkinter has no table widget, so this wraps ``ttk.Treeview`` (the
documented Tkinter fallback) and styles it from the theme palette. Every list
screen uses this one component instead of copy-pasting table code.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from models.common import Page
from ui.theme import TABLE_STYLE, Theme

# Row tags understood by every table, mapped to palette bases.
TAG_LOW = "low"
TAG_STOCKOUT = "stockout"
TAG_INACTIVE = "inactive"
TAG_ERROR = "error"
TAG_WARNING = "warning"

Row = tuple[str, Sequence[Any], tuple[str, ...]]  # (row id, values, tags)


@dataclass(frozen=True)
class Column:
    """Definition of one table column.

    Attributes:
        key: Field key; also the sort key passed to services.
        heading: Header text.
        width: Initial width in pixels.
        anchor: ``w`` (left), ``e`` (right) or ``center``.
        sortable: Whether clicking the header sorts by this column.
    """

    key: str
    heading: str
    width: int = 120
    anchor: str = "w"
    sortable: bool = True


class DataTable(ctk.CTkFrame):
    """Sortable, paginated table.

    Args:
        master: Parent widget.
        theme: Shared theme.
        columns: Column definitions.
        on_sort: Called with ``(key, descending)`` when a header is clicked.
        on_page: Called with the requested page number; ``None`` hides the pager.
        on_activate: Called with the row id on double-click or Enter.
        height: Visible rows.
    """

    def __init__(
        self,
        master: Any,
        theme: Theme,
        columns: Sequence[Column],
        on_sort: Callable[[str, bool], None] | None = None,
        on_page: Callable[[int], None] | None = None,
        on_activate: Callable[[str], None] | None = None,
        height: int = 15,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._theme = theme
        self._columns = {c.key: c for c in columns}
        self._on_sort = on_sort
        self._on_page = on_page
        self._on_activate = on_activate
        self._sort_key: str | None = None
        self._descending = False
        self._page = 1
        self._build_tree(columns, height)
        self._build_pager()
        self.apply_tag_colors()
        theme.on_change(self.apply_tag_colors)
        self.bind("<Destroy>", self._on_destroy, add="+")

    # -- construction ---------------------------------------------------------------
    def _build_tree(self, columns: Sequence[Column], height: int) -> None:
        """Create the Treeview and its scrollbar."""
        holder = ctk.CTkFrame(self, fg_color="transparent")
        holder.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(holder, columns=[c.key for c in columns], show="headings",
                                 selectmode="browse", height=height, style=TABLE_STYLE)
        for column in columns:
            self.tree.heading(column.key, text=column.heading,
                              command=lambda key=column.key: self._header_clicked(key))
            self.tree.column(column.key, width=column.width, minwidth=40, anchor=column.anchor)
        scrollbar = ctk.CTkScrollbar(holder, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._activated)
        self.tree.bind("<Return>", self._activated)

    def _build_pager(self) -> None:
        """Create the previous/next controls and the page label."""
        self._pager = ctk.CTkFrame(self, fg_color="transparent")
        self._info = ctk.CTkLabel(self._pager, text="", font=self._theme.font(-1))
        self._next = ctk.CTkButton(self._pager, text="Next ›", width=80,
                                   command=lambda: self._go(self._page + 1))
        self._prev = ctk.CTkButton(self._pager, text="‹ Prev", width=80,
                                   command=lambda: self._go(self._page - 1))
        self._info.pack(side="left", padx=4)
        self._next.pack(side="right", padx=(6, 0))
        self._prev.pack(side="right")
        if self._on_page is not None:
            self._pager.pack(fill="x", pady=(8, 0))

    # -- data -----------------------------------------------------------------------
    def set_rows(self, rows: Iterable[Row]) -> None:
        """Replace every row; selection is restored when the same id reappears."""
        selected = self.selected_id()
        self.tree.delete(*self.tree.get_children())
        for row_id, values, tags in rows:
            self.tree.insert("", "end", iid=row_id, values=list(values), tags=tags)
        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected)

    def set_page(self, page: Page[Any], rows: Iterable[Row]) -> None:
        """Show one page of rows and update the pager."""
        self.set_rows(rows)
        self._page = page.page
        first = 0 if page.total == 0 else (page.page - 1) * page.page_size + 1
        last = min(page.page * page.page_size, page.total)
        self._info.configure(
            text=f"Rows {first}–{last} of {page.total}   ·   Page {page.page} of {page.pages}")
        self._prev.configure(state="normal" if page.has_previous else "disabled")
        self._next.configure(state="normal" if page.has_next else "disabled")

    def selected_id(self) -> str | None:
        """Id of the selected row, or ``None``."""
        selection = self.tree.selection()
        return selection[0] if selection else None

    def row_values(self, row_id: str) -> list[Any]:
        """Displayed values of one row."""
        return list(self.tree.item(row_id, "values"))

    # -- styling --------------------------------------------------------------------
    def apply_tag_colors(self) -> None:
        """(Re)apply status colours for the current light/dark mode."""
        theme = self._theme
        self.tree.tag_configure(TAG_LOW, background=theme.mode_color("danger_row"))
        self.tree.tag_configure(TAG_STOCKOUT, background=theme.mode_color("stockout_row"))
        self.tree.tag_configure(TAG_INACTIVE, foreground=theme.mode_color("inactive_fg"))
        self.tree.tag_configure(TAG_ERROR, foreground=theme.color("danger"))
        self.tree.tag_configure(TAG_WARNING, foreground=theme.color("warning"))

    def mark_sorted(self, key: str, descending: bool) -> None:
        """Show the sort arrow on ``key`` (used to display the initial sort)."""
        self._sort_key, self._descending = key, descending
        for column in self._columns.values():
            arrow = (" ▼" if descending else " ▲") if column.key == key else ""
            self.tree.heading(column.key, text=f"{column.heading}{arrow}")

    # -- events ---------------------------------------------------------------------
    def _header_clicked(self, key: str) -> None:
        """Toggle the sort direction and notify the owner."""
        if not self._columns[key].sortable or self._on_sort is None:
            return
        descending = not self._descending if key == self._sort_key else False
        self.mark_sorted(key, descending)
        self._on_sort(key, descending)

    def _go(self, page: int) -> None:
        """Request another page."""
        if self._on_page is not None:
            self._on_page(page)

    def _activated(self, _event: object) -> None:
        """Forward double-click / Enter on a row."""
        row_id = self.selected_id()
        if row_id and self._on_activate is not None:
            self._on_activate(row_id)

    def _on_destroy(self, event: Any) -> None:
        """Unregister the theme listener when the table is destroyed."""
        if event.widget is self:
            self._theme.remove_listener(self.apply_tag_colors)
