"""Reusable data table: ttk.Treeview + scrollbar + clickable sort + optional pager.

CustomTkinter has no table widget, so this wraps ``ttk.Treeview`` (the
documented Tkinter fallback) and styles it from the theme palette. Every list
screen uses this one component instead of copy-pasting table code.

Column definitions and row tags live in :mod:`ui.components.table_types` and
are re-exported here for convenience.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from models.common import Page
from ui.components.pager import Pager
from ui.components.table_types import (
    TAG_ERROR,
    TAG_INACTIVE,
    TAG_LOW,
    TAG_STOCKOUT,
    TAG_SUCCESS,
    TAG_WARNING,
    Column,
    Row,
)
from ui.theme import TABLE_STYLE, Theme

__all__ = ["TAG_ERROR", "TAG_INACTIVE", "TAG_LOW", "TAG_STOCKOUT", "TAG_SUCCESS", "TAG_WARNING",
           "Column", "DataTable", "Row"]

class DataTable(ctk.CTkFrame):
    """Sortable table with an optional pager.

    Args:
        master: Parent widget.
        theme: Shared theme.
        columns: Column definitions.
        on_sort: Called with ``(key, descending)`` when a header is clicked.
        on_page: Called with the requested page number; ``None`` hides the pager.
        on_activate: Called with the row id on double-click or Enter.
        height: Visible rows.
    """

    def __init__(self, master: Any, theme: Theme, columns: Sequence[Column],
                 on_sort: Callable[[str, bool], None] | None = None,
                 on_page: Callable[[int], None] | None = None,
                 on_activate: Callable[[str], None] | None = None, height: int = 15) -> None:
        super().__init__(master, fg_color="transparent")
        self._theme = theme
        self._columns = {c.key: c for c in columns}
        self._on_sort = on_sort
        self._on_activate = on_activate
        self._sort_key: str | None = None
        self._descending = False
        self._build_tree(columns, height)
        self._pager = Pager(self, theme, on_page) if on_page is not None else None
        if self._pager is not None:
            self._pager.pack(fill="x", pady=(8, 0))
        self.apply_tag_colors()
        theme.on_change(self.apply_tag_colors)

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

    # -- data -----------------------------------------------------------------------
    def set_rows(self, rows: Iterable[Row]) -> None:
        """Replace every row, keeping the selection when the same id reappears.

        Args:
            rows: ``(row id, values, tags)`` triples.
        """
        selected = self.selected_id()
        self.tree.delete(*self.tree.get_children())
        for row_id, values, tags in rows:
            self.tree.insert("", "end", iid=row_id, values=list(values), tags=tags)
        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected)

    def set_page(self, page: Page[Any], rows: Iterable[Row]) -> None:
        """Show one page of rows and update the pager.

        Args:
            page: The page being displayed (for the pager text and buttons).
            rows: Rows built from ``page.items``.
        """
        self.set_rows(rows)
        if self._pager is not None:
            self._pager.update_page(page)

    def selected_id(self) -> str | None:
        """Id of the selected row.

        Returns:
            The row id, or ``None`` when nothing is selected.
        """
        selection = self.tree.selection()
        return selection[0] if selection else None

    def row_values(self, row_id: str) -> list[Any]:
        """Displayed values of one row.

        Args:
            row_id: Row identifier.

        Returns:
            The cell texts in column order.
        """
        return list(self.tree.item(row_id, "values"))

    # -- styling --------------------------------------------------------------------
    def apply_tag_colors(self) -> None:
        """(Re)apply status colours for the current light/dark mode."""
        theme, tags = self._theme, self.tree.tag_configure
        tags(TAG_LOW, background=theme.mode_color("danger_row"))
        tags(TAG_STOCKOUT, background=theme.mode_color("stockout_row"))
        tags(TAG_INACTIVE, foreground=theme.mode_color("inactive_fg"))
        tags(TAG_ERROR, foreground=theme.color("danger"))
        tags(TAG_WARNING, foreground=theme.color("warning"))
        tags(TAG_SUCCESS, foreground=theme.color("success"))

    def mark_sorted(self, key: str, descending: bool) -> None:
        """Show the sort arrow on a column header.

        Args:
            key: Column key being sorted.
            descending: Sort direction.
        """
        self._sort_key, self._descending = key, descending
        for column in self._columns.values():
            arrow = (" ▼" if descending else " ▲") if column.key == key else ""
            self.tree.heading(column.key, text=f"{column.heading}{arrow}")

    def destroy(self) -> None:
        """Unregister the theme listener, then destroy the widget."""
        self._theme.remove_listener(self.apply_tag_colors)
        super().destroy()

    # -- events ---------------------------------------------------------------------
    def _header_clicked(self, key: str) -> None:
        """Toggle the sort direction and notify the owner."""
        if not self._columns[key].sortable or self._on_sort is None:
            return
        descending = not self._descending if key == self._sort_key else False
        self.mark_sorted(key, descending)
        self._on_sort(key, descending)

    def _activated(self, _event: object) -> None:
        """Forward double-click / Enter on a row."""
        row_id = self.selected_id()
        if row_id and self._on_activate is not None:
            self._on_activate(row_id)
