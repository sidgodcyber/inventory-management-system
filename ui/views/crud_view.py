"""Generic CRUD screen: a :class:`ListView` plus add / edit / delete flows.

Concrete screens (categories, suppliers, products) only describe their
columns, form fields and which service methods to call. The toolbar,
dialogs, confirmation, error handling and toasts live here once.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ui.components.confirm_dialog import ask_confirm
from ui.components.form_dialog import FormDialog, FormField
from ui.views.list_view import ListView


class CrudView(ListView):
    """Template for searchable, paginated CRUD screens.

    Subclasses set :attr:`entity` and :attr:`columns` and implement ``fetch``,
    ``to_row``, ``load``, ``form_fields``, ``save`` and ``remove``.
    """

    #: Singular entity name used in titles and messages, e.g. "Category".
    entity: str = "Item"
    #: Search box hint.
    search_hint: str = "Search…"

    def build_above_table(self) -> None:
        """Toolbar with search and actions, then an optional filter row."""
        self.toolbar = self.make_toolbar(self.search_hint)
        self.add_buttons()
        filters = ctk.CTkFrame(self.body, fg_color="transparent")
        self.build_filters(filters)
        if filters.winfo_children():
            filters.pack(fill="x", pady=(0, 10))

    def add_buttons(self) -> None:
        """Default toolbar buttons (packed right to left); override to add more."""
        self.toolbar.add_button("Delete", self._delete_selected, "danger", width=90)
        self.toolbar.add_button("Edit", self._edit_selected, "secondary", width=80)
        self.toolbar.add_button(f"+ Add {self.entity.lower()}", self._add, width=140)

    def build_filters(self, frame: Any) -> None:
        """Extra filter widgets in a row under the toolbar (override).

        Args:
            frame: Container to pack the filter widgets into.
        """

    # -- hooks ------------------------------------------------------------------------
    def load(self, item_id: int) -> Any:
        """Load one record for editing (override).

        Args:
            item_id: Primary key.

        Returns:
            The record.
        """
        raise NotImplementedError

    def form_fields(self, item: Any | None) -> list[FormField]:
        """Fields for the form (override).

        Args:
            item: ``None`` when adding, otherwise the record being edited.

        Returns:
            Field definitions in display order.
        """
        raise NotImplementedError

    def initial_values(self, item: Any | None) -> dict[str, Any]:
        """Form pre-fill values (defaults to the record's attributes).

        Args:
            item: ``None`` when adding, otherwise the record being edited.

        Returns:
            ``{field key: value}``.
        """
        return {} if item is None else dict(vars(item))

    def save(self, values: dict[str, str], item_id: int | None) -> Any:
        """Create or update a record through a service (override).

        Args:
            values: Form values.
            item_id: ``None`` to create, otherwise the record to update.

        Returns:
            Whatever the service returned (passed to :meth:`after_save`).
        """
        raise NotImplementedError

    def remove(self, item_id: int) -> str:
        """Delete a record through a service (override).

        Args:
            item_id: Record to delete.

        Returns:
            Message shown in the status bar.
        """
        raise NotImplementedError

    def after_save(self, result: Any) -> None:
        """Feedback after a successful save (override for warnings).

        Args:
            result: Value returned by :meth:`save`.
        """
        self.notify(f"{self.entity} saved.", "success")

    def on_activate(self, row_id: str) -> None:
        """Double-click / Enter opens the edit form.

        Args:
            row_id: Identifier of the activated row.
        """
        self._edit_row(row_id)

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
        """Load the record and open the edit form."""
        item = self.guarded(f"{self.title} > Open", lambda: self.load(int(row_id)))
        if item is not None:
            self._open_form(item)

    def _open_form(self, item: Any | None) -> None:
        """Show the form dialog in add or edit mode."""
        item_id = None if item is None else int(item.id)
        action = "Add" if item_id is None else "Edit"
        context = f"{self.title} > {action}"
        FormDialog(self, self.theme, f"{action} {self.entity.lower()}", self.form_fields(item),
                   on_submit=lambda values: self.form_call(
                       context, lambda: self.save(values, item_id), self._saved),
                   initial=self.initial_values(item))

    def _saved(self, result: Any) -> None:
        """Feedback and refresh after a successful save."""
        self.after_save(result)
        self.load_page()
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
            self.load_page()
            self.app.refresh_badge()

    def _require_selection(self, verb: str) -> str | None:
        """Return the selected row id or ask the operator to pick one."""
        row_id = self.table.selected_id()
        if row_id is None:
            self.notify(f"Select a {self.entity.lower()} to {verb} first.", "warning")
        return row_id
