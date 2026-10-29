"""Generic list screen with search, sort, pagination and add/edit/delete flows.

Concrete screens (categories, suppliers, products) only describe their
columns, form fields and which service methods to call. Everything else
(toolbar, table, dialogs, confirmation, error handling, toasts) lives here
once, which is the main maintainability lever of the UI layer.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import customtkinter as ctk

from models.common import ListQuery, Page
from ui.components.confirm_dialog import ask_confirm
from ui.components.data_table import Column, DataTable, Row
from ui.components.form_dialog import FormDialog, FormField
from ui.components.toolbar import Toolbar
from ui.views.base_view import BaseView


class CrudView(BaseView):
    """Template for searchable, paginated CRUD screens.

    Subclasses set :attr:`entity` and :attr:`columns` and implement the
    ``fetch``/``to_row``/``form_fields``/``save``/``remove`` hooks.
    """

    #: Singular entity name used in titles and messages, e.g. "Category".
    entity: str = "Item"
    #: Table columns.
    columns: Sequence[Column] = ()
    #: Initial sort column key.
    default_sort: str = "name"
    #: Search box hint.
    search_hint: str = "Search…"

    def build(self) -> None:
        """Toolbar, optional filters and the data table."""
        self.query = ListQuery(sort_by=self.default_sort,
                               page_size=self.setting("page_size"))
        self.toolbar = Toolbar(self.body, self.theme, self._on_search,
                               self.services.config.get("ui.search_debounce_ms"),
                               self.search_hint)
        self.toolbar.pack(fill="x", pady=(0, 10))
        self.add_buttons()
        filters = ctk.CTkFrame(self.body, fg_color="transparent")
        self.build_filters(filters)
        if filters.winfo_children():
            filters.pack(fill="x", pady=(0, 10))
        self.table = DataTable(self.body, self.theme, self.columns, on_sort=self._on_sort,
                               on_page=self._on_page, on_activate=self._edit_row)
        self.table.pack(fill="both", expand=True)
        self.table.mark_sorted(self.query.sort_by, self.query.descending)

    def add_buttons(self) -> None:
        """Default toolbar buttons (right to left); override to add more."""
        self.toolbar.add_button("Delete", self._delete_selected, "danger", width=90)
        self.toolbar.add_button("Edit", self._edit_selected, "secondary", width=80)
        self.toolbar.add_button(f"+ Add {self.entity.lower()}", self._add, width=140)

    def build_filters(self, frame: Any) -> None:
        """Extra filter widgets in a row under the toolbar (override)."""

    # -- hooks ------------------------------------------------------------------------
    def fetch(self, query: ListQuery) -> Page[Any]:
        """Load one page of records (override)."""
        raise NotImplementedError

    def to_row(self, item: Any) -> Row:
        """Convert a record to ``(row id, values, tags)`` (override)."""
        raise NotImplementedError

    def load(self, item_id: int) -> Any:
        """Load one record for editing (override)."""
        raise NotImplementedError

    def form_fields(self, item: Any | None) -> list[FormField]:
        """Fields for the add (``item is None``) or edit form (override)."""
        raise NotImplementedError

    def initial_values(self, item: Any | None) -> dict[str, Any]:
        """Form pre-fill values; defaults to the record's attributes."""
        return {} if item is None else dict(vars(item))

    def save(self, values: dict[str, str], item_id: int | None) -> Any:
        """Create (``item_id is None``) or update a record (override)."""
        raise NotImplementedError

    def remove(self, item_id: int) -> str:
        """Delete a record and return a toast message (override)."""
        raise NotImplementedError

    def after_save(self, result: Any) -> None:
        """Feedback after a successful save (override for warnings)."""
        self.notify(f"{self.entity} saved.", "success")

    # -- data loading -----------------------------------------------------------------
    def refresh(self) -> None:
        """Reload the current page with the latest page-size setting."""
        self.query.page_size = self.setting("page_size")
        page = self.guarded(f"{self.title} > Load", lambda: self.fetch(self.query))
        if page is not None:
            self.table.set_page(page, [self.to_row(item) for item in page.items])

    def _on_search(self, text: str) -> None:
        """New search text: back to page 1."""
        self.query.search, self.query.page = text, 1
        self.refresh()

    def _on_sort(self, key: str, descending: bool) -> None:
        """Header clicked."""
        self.query.sort_by, self.query.descending = key, descending
        self.refresh()

    def _on_page(self, page: int) -> None:
        """Pager clicked."""
        self.query.page = page
        self.refresh()

    # -- flows ------------------------------------------------------------------------
    def _add(self) -> None:
        """Open an empty form."""
        self._open_form(None)

    def _edit_selected(self) -> None:
        """Open the form for the selected row."""
        row_id = self._require_selection("edit")
        if row_id:
            self._edit_row(row_id)

    def _edit_row(self, row_id: str) -> None:
        """Open the form for ``row_id`` (also used on double-click)."""
        item = self.guarded(f"{self.title} > Open", lambda: self.load(int(row_id)))
        if item is not None:
            self._open_form(item)

    def _open_form(self, item: Any | None) -> None:
        """Show the form dialog in add or edit mode."""
        item_id = None if item is None else int(item.id)
        action = "Add" if item_id is None else "Edit"
        context = f"{self.title} > {action}"
        FormDialog(
            self, self.theme, f"{action} {self.entity.lower()}", self.form_fields(item),
            on_submit=lambda values: self.form_call(
                context, lambda: self.save(values, item_id), self._saved),
            initial=self.initial_values(item),
        )

    def _saved(self, result: Any) -> None:
        """Refresh after a successful save."""
        self.after_save(result)
        self.refresh()
        self.app.refresh_badge()

    def _delete_selected(self) -> None:
        """Confirm, then delete the selected record."""
        row_id = self._require_selection("delete")
        if not row_id:
            return
        label = self.table.row_values(row_id)[0]
        if not ask_confirm(self, self.theme, f"Delete {self.entity.lower()}",
                           f"Delete {self.entity.lower()} '{label}'? This cannot be undone.",
                           "Delete", danger=True):
            return
        message = self.guarded(f"{self.title} > Delete", lambda: self.remove(int(row_id)))
        if message:
            self.notify(message, "success")
            self.refresh()
            self.app.refresh_badge()

    def _require_selection(self, verb: str) -> str | None:
        """Return the selected row id or tell the operator to pick one."""
        row_id = self.table.selected_id()
        if row_id is None:
            self.notify(f"Select a {self.entity.lower()} to {verb} first.", "warning")
        return row_id
