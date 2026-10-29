"""Base class for screens built around one sortable, paginated table.

Owns the :class:`~models.common.ListQuery` (search, sort, page, page size from
settings) and the load/sort/page plumbing, so the CRUD screens, the stock
history and the activity log share one implementation instead of three.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from models.common import ListQuery, Page
from ui.components.data_table import Column, DataTable, Row
from ui.components.toolbar import Toolbar
from ui.views.base_view import BaseView


class ListView(BaseView):
    """Screen with widgets above a :class:`DataTable` and optional widgets below.

    Subclasses set :attr:`columns` and implement :meth:`fetch` and :meth:`to_row`.
    """

    #: Table columns.
    columns: Sequence[Column] = ()
    #: Initial sort column and direction.
    default_sort: str = "name"
    default_descending: bool = False
    #: Visible table rows.
    table_height: int = 15

    def build(self) -> None:
        """Create the query, the area above the table, the table and the area below."""
        self.query = ListQuery(sort_by=self.default_sort, descending=self.default_descending,
                               page_size=self.setting("page_size"))
        self.build_above_table()
        self.table = DataTable(self.body, self.theme, self.columns, on_sort=self._on_sort,
                               on_page=self._on_page, on_activate=self.on_activate,
                               height=self.table_height)
        self.table.pack(fill="both", expand=True)
        self.table.mark_sorted(self.query.sort_by, self.query.descending)
        self.build_below_table()

    # -- hooks ------------------------------------------------------------------------
    def build_above_table(self) -> None:
        """Toolbars, filters or panels shown above the table (override)."""

    def build_below_table(self) -> None:
        """Widgets shown below the table, e.g. a details pane (override)."""

    def fetch(self, query: ListQuery) -> Page[Any]:
        """Load one page of records from a service (override).

        Args:
            query: Current search, sort and page.

        Returns:
            The requested page.
        """
        raise NotImplementedError

    def to_row(self, item: Any) -> Row:
        """Convert a record into a table row (override).

        Args:
            item: One record from :meth:`fetch`.

        Returns:
            ``(row id, values, tags)``.
        """
        raise NotImplementedError

    def on_activate(self, row_id: str) -> None:
        """Handle double-click / Enter on a row (override).

        Args:
            row_id: Identifier of the activated row.
        """

    def after_load(self, page: Page[Any]) -> None:
        """Run after a page is displayed (override).

        Args:
            page: The page just shown.
        """

    # -- loading ----------------------------------------------------------------------
    def make_toolbar(self, hint: str) -> Toolbar:
        """Create and pack a toolbar whose search box drives this list.

        Args:
            hint: Placeholder text for the search box.

        Returns:
            The toolbar, ready for :meth:`Toolbar.add_button` calls.
        """
        toolbar = Toolbar(self.body, self.theme, self.search,
                          self.services.config.get("ui.search_debounce_ms"), hint)
        toolbar.pack(fill="x", pady=(0, 8))
        return toolbar

    def refresh(self) -> None:
        """Reload the current page (screens with extra data override and call super)."""
        self.load_page()

    def load_page(self) -> None:
        """Fetch and display the current page with the latest page-size setting."""
        self.query.page_size = self.setting("page_size")
        page = self.guarded(f"{self.title} > Load", lambda: self.fetch(self.query))
        if page is not None:
            self.table.set_page(page, [self.to_row(item) for item in page.items])
            self.after_load(page)

    def search(self, text: str) -> None:
        """Apply new search text and go back to the first page.

        Args:
            text: Search text from the toolbar.
        """
        self.query.search = text
        self.first_page()

    def first_page(self) -> None:
        """Show page 1 (after any filter change)."""
        self.query.page = 1
        self.load_page()

    def _on_sort(self, key: str, descending: bool) -> None:
        """Header clicked."""
        self.query.sort_by, self.query.descending = key, descending
        self.load_page()

    def _on_page(self, page: int) -> None:
        """Pager clicked."""
        self.query.page = page
        self.load_page()
