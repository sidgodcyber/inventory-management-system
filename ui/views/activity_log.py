"""Activity Log screen: filter, inspect, export and purge the audit trail.

Shows every business event written by ``log_activity`` (who did what, to which
record, when, with old -> new values). ``ERROR`` entries are the raw data for
the defect checksheet and Pareto analysis in later TQM reviews.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import customtkinter as ctk

from models.activity_log import ActivityLog
from models.common import ListQuery
from models.filters import ActivityFilter
from ui.components.confirm_dialog import ask_confirm
from ui.components.data_table import TAG_ERROR, TAG_WARNING, Column, DataTable, Row
from ui.components.messages import show_info
from ui.components.toolbar import Toolbar
from ui.views.base_view import BaseView
from utils.formatters import truncate
from utils.validators import Validator

ANY = "All"
_LEVEL_TAGS = {"ERROR": (TAG_ERROR,), "CRITICAL": (TAG_ERROR,), "WARNING": (TAG_WARNING,)}
_SUMMARY_LENGTH = 90


class ActivityLogView(BaseView):
    """Browse the audit trail with filters and a details pane."""

    title = "Activity Log"
    subtitle = ("Every create, update, delete, stock movement, settings change, export and "
                "error, with the operator, time and old → new values.")
    columns = (
        Column("timestamp", "Timestamp", 140),
        Column("user", "User", 100),
        Column("action", "Action", 120),
        Column("entity", "Entity", 110),
        Column("entity_id", "ID", 110),
        Column("level", "Level", 70, "center"),
        Column("details", "Summary", 385, sortable=False),
    )

    def build(self) -> None:
        """Toolbar, filter row, table and details pane."""
        self._entries: dict[str, ActivityLog] = {}
        self.query = ListQuery(sort_by="timestamp", descending=True,
                               page_size=self.setting("page_size"))
        self.filters = ActivityFilter()
        self._build_toolbar()
        self._build_filters()
        self.table = DataTable(self.body, self.theme, self.columns, on_sort=self._on_sort,
                               on_page=self._on_page, height=8)
        self.table.pack(fill="both", expand=True)
        self.table.mark_sorted(self.query.sort_by, self.query.descending)
        self.table.tree.bind("<<TreeviewSelect>>", lambda _e: self._show_details(), add="+")
        self.details = ctk.CTkTextbox(self.body, height=96, font=self.theme.font(-1),
                                      wrap="word")
        self.details.pack(fill="x", pady=(8, 0))

    def _build_toolbar(self) -> None:
        """Search in details plus export and purge actions."""
        self.toolbar = Toolbar(self.body, self.theme, self._on_search,
                               self.services.config.get("ui.search_debounce_ms"),
                               "Search details or record ID…")
        self.toolbar.pack(fill="x", pady=(0, 8))
        self.toolbar.add_button("Purge old entries", self._purge, "danger", width=140)
        self.toolbar.add_button("Export CSV", self._export, "secondary", width=100)

    def _build_filters(self) -> None:
        """Date range, action, entity and user filters."""
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", pady=(0, 8))
        self.date_from = ctk.CTkEntry(row, width=130)
        self.date_to = ctk.CTkEntry(row, width=130)
        self.action = ctk.CTkOptionMenu(row, values=[ANY], width=145)
        self.entity = ctk.CTkOptionMenu(row, values=[ANY], width=130)
        self.user = ctk.CTkOptionMenu(row, values=[ANY], width=120)
        for label, widget in (("From", self.date_from), ("To", self.date_to),
                              ("Action", self.action), ("Entity", self.entity),
                              ("User", self.user)):
            ctk.CTkLabel(row, text=label, font=self.theme.font(-1)).pack(side="left",
                                                                         padx=(0, 4))
            widget.pack(side="left", padx=(0, 10))
        ctk.CTkButton(row, text="Clear", width=70, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"), command=self._clear).pack(side="right")
        ctk.CTkButton(row, text="Apply", width=70, command=self._apply).pack(
            side="right", padx=(0, 6))

    # -- filters ------------------------------------------------------------------------
    def _read_filters(self) -> ActivityFilter:
        """Build a filter from the widgets (dates use the date-format setting)."""
        fmt = self.setting("date_format")
        pick = lambda widget: None if widget.get() == ANY else widget.get()  # noqa: E731
        return ActivityFilter(
            date_from=Validator.date(self.date_from.get(), "From date", fmt),
            date_to=Validator.date(self.date_to.get(), "To date", fmt),
            action=pick(self.action), entity=pick(self.entity), user=pick(self.user),
        )

    def _apply(self) -> None:
        """Apply the filter widgets."""
        filters = self.guarded("Activity Log > Filter", self._read_filters)
        if filters is not None:
            self.filters, self.query.page = filters, 1
            self.load_page()

    def _clear(self) -> None:
        """Reset every filter and the search box."""
        for entry in (self.date_from, self.date_to, self.toolbar.search):
            entry.delete(0, "end")
        for menu in (self.action, self.entity, self.user):
            menu.set(ANY)
        self.filters, self.query.search, self.query.page = ActivityFilter(), "", 1
        self.load_page()

    def _on_search(self, text: str) -> None:
        """Search text changed."""
        self.query.search, self.query.page = text, 1
        self.load_page()

    def _on_sort(self, key: str, descending: bool) -> None:
        """Header clicked."""
        self.query.sort_by, self.query.descending = key, descending
        self.load_page()

    def _on_page(self, page: int) -> None:
        """Pager clicked."""
        self.query.page = page
        self.load_page()

    # -- data ---------------------------------------------------------------------------
    def refresh(self) -> None:
        """Reload filter choices, date hints and the current page."""
        options = self.guarded("Activity Log > Load filters",
                               self.services.activity.filter_options)
        if options:
            self.action.configure(values=[ANY, *options["actions"]])
            self.entity.configure(values=[ANY, *options["entities"]])
            self.user.configure(values=[ANY, *options["users"]])
        example = f"e.g. {self._today_text()}"
        self.date_from.configure(placeholder_text=example)
        self.date_to.configure(placeholder_text=example)
        self.load_page()

    def _today_text(self) -> str:
        """Today's date in the configured format."""
        return date.today().strftime(self.setting("date_format"))

    def load_page(self) -> None:
        """Fetch and show one page of entries."""
        self.query.page_size = self.setting("page_size")
        page = self.guarded("Activity Log > Load",
                            lambda: self.services.activity.find(self.filters, self.query))
        if page is None:
            return
        self._entries = {str(entry.id): entry for entry in page.items}
        self.table.set_page(page, [self._to_row(entry) for entry in page.items])
        self._show_details()

    def _to_row(self, entry: ActivityLog) -> Row:
        """Table row with a one-line summary of the details."""
        values = (self.datetime_text(entry.timestamp), entry.user, entry.action, entry.entity,
                  entry.entity_id or "", entry.level,
                  truncate(summarize(entry.details), _SUMMARY_LENGTH))
        return str(entry.id), values, _LEVEL_TAGS.get(entry.level, ())

    def _show_details(self) -> None:
        """Pretty-print the selected entry's details JSON."""
        entry = self._entries.get(self.table.selected_id() or "")
        text = ("Select an entry to see its full details (old → new values, error context)."
                if entry is None else
                f"#{entry.id}  {entry.timestamp}  {entry.user}  {entry.action} "
                f"{entry.entity} {entry.entity_id or ''}\n{summarize(entry.details)}\n\n"
                f"{json.dumps(entry.details, indent=2, ensure_ascii=False)}")
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", text)
        self.details.configure(state="disabled")

    # -- actions ------------------------------------------------------------------------
    def _export(self) -> None:
        """Export the filtered entries to CSV."""
        path = self.guarded("Activity Log > Export",
                            lambda: self.services.activity.export_csv(self.filters))
        if path:
            self.notify(f"Exported {path.name}", "success")
            show_info(self, "Export complete", f"Activity log saved to:\n{path}")

    def _purge(self) -> None:
        """Delete entries older than the retention setting, after confirmation."""
        activity = self.services.activity
        count = self.guarded("Activity Log > Purge", activity.expired_count)
        if count is None:
            return
        days = activity.retention_days()
        if count == 0:
            self.notify(f"No entries are older than {days} days.", "info")
            return
        if ask_confirm(self, self.theme, "Purge activity log",
                       f"Permanently delete {count} entries older than {days} days "
                       "(the retention setting)? The purge itself will be logged.",
                       "Purge", danger=True):
            removed = self.guarded("Activity Log > Purge", activity.purge_expired)
            if removed is not None:
                self.notify(f"Purged {removed} old entries.", "success")
                self.refresh()


def summarize(details: dict[str, Any]) -> str:
    """One-line, human-readable summary of an activity payload."""
    if "changes" in details:
        return "; ".join(f"{key}: {_short(c.get('old'))} → {_short(c.get('new'))}"
                         for key, c in details["changes"].items())
    if "quantity_on_hand" in details:
        qty = details["quantity_on_hand"]
        return (f"{details.get('sku', '')} qty {details.get('quantity')}: "
                f"{qty.get('old')} → {qty.get('new')}  {details.get('note', '')}").strip()
    if {"old", "new"} <= details.keys() and not isinstance(details["new"], dict):
        return f"{_short(details['old'])} → {_short(details['new'])}"
    if "message" in details:
        return f"[{details.get('context', '')}] {details.get('type', '')}: {details['message']}"
    return ", ".join(f"{key}={_short(value)}" for key, value in details.items())


def _short(value: Any) -> str:
    """Compact text for a value inside a summary."""
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {v}" for k, v in value.items()) + "}"
    return str(value)
