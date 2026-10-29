"""Activity Log screen: filter, inspect, export and purge the audit trail.

Shows every business event written by ``log_activity`` (who did what, to which
record, when, with old -> new values). ``ERROR`` entries are the raw data for
the defect checksheet and Pareto analysis in later TQM reviews.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from datetime import date

from models.activity_log import ActivityLog
from models.common import ListQuery, Page
from models.filters import ActivityFilter
from ui.components.confirm_dialog import ask_confirm
from ui.components.data_table import TAG_ERROR, TAG_WARNING, Column, Row
from ui.components.messages import show_info
from ui.views.activity_details import ActivityDetails
from ui.views.activity_filters import ActivityFilterBar
from ui.views.activity_summary import summarize
from ui.views.list_view import ListView
from utils.formatters import truncate

__all__ = ["ActivityLogView", "summarize"]

_LEVEL_TAGS = {"ERROR": (TAG_ERROR,), "CRITICAL": (TAG_ERROR,), "WARNING": (TAG_WARNING,)}
_SUMMARY_LENGTH = 90


class ActivityLogView(ListView):
    """Browse the audit trail with filters and a details pane."""

    title = "Activity Log"
    subtitle = ("Every create, update, delete, stock movement, settings change, export and "
                "error, with the operator, time and old → new values.")
    default_sort = "timestamp"
    default_descending = True
    table_height = 8
    columns = (
        Column("timestamp", "Timestamp", 140), Column("user", "User", 100),
        Column("action", "Action", 120), Column("entity", "Entity", 110),
        Column("entity_id", "ID", 110), Column("level", "Level", 70, "center"),
        Column("details", "Summary", 385, sortable=False),
    )

    def build(self) -> None:
        """Initialise filter state, then the list layout."""
        self.filters = ActivityFilter()
        self._entries: dict[str, ActivityLog] = {}
        super().build()

    def build_above_table(self) -> None:
        """Search toolbar with export/purge, then the filter row."""
        self.toolbar = self.make_toolbar("Search details or record ID…")
        self.toolbar.add_button("Purge old entries", self._purge, "danger", width=140)
        self.toolbar.add_button("Export CSV", self._export, "secondary", width=100)
        self.filter_bar = ActivityFilterBar(self.body, self.theme, self._apply, self._cleared)
        self.filter_bar.pack(fill="x", pady=(0, 8))

    def build_below_table(self) -> None:
        """Read-only details pane for the selected entry."""
        self.details = ActivityDetails(self.body, self.theme)
        self.details.pack(fill="x", pady=(8, 0))
        self.table.tree.bind("<<TreeviewSelect>>", lambda _e: self.show_details(), add="+")

    # -- ListView hooks -----------------------------------------------------------------
    def fetch(self, query: ListQuery) -> Page[ActivityLog]:
        """One page of filtered entries.

        Args:
            query: Search, sort and page.

        Returns:
            The requested page.
        """
        return self.services.activity.find(self.filters, query)

    def to_row(self, item: ActivityLog) -> Row:
        """Table row with a one-line summary; errors red, warnings amber.

        Args:
            item: Activity entry.

        Returns:
            ``(row id, values, tags)``.
        """
        values = (self.datetime_text(item.timestamp), item.user, item.action, item.entity,
                  item.entity_id or "", item.level,
                  truncate(summarize(item.details), _SUMMARY_LENGTH))
        return str(item.id), values, _LEVEL_TAGS.get(item.level, ())

    def after_load(self, page: Page[ActivityLog]) -> None:
        """Remember the shown entries for the details pane.

        Args:
            page: The page just displayed.
        """
        self._entries = {str(entry.id): entry for entry in page.items}
        self.show_details()

    def refresh(self) -> None:
        """Reload filter choices and the current page."""
        options = self.guarded("Activity Log > Load filters",
                               self.services.activity.filter_options)
        if options:
            self.filter_bar.set_options(options,
                                        date.today().strftime(self.setting("date_format")))
        self.load_page()

    # -- details ------------------------------------------------------------------------
    def show_details(self) -> None:
        """Show the selected entry in the details pane."""
        self.details.show(self._entries.get(self.table.selected_id() or ""))

    # -- actions ------------------------------------------------------------------------
    def _apply(self) -> None:
        """Read the filter row and show page 1."""
        filters = self.guarded("Activity Log > Filter",
                               lambda: self.filter_bar.read(self.setting("date_format")))
        if filters is not None:
            self.filters = filters
            self.first_page()

    def _cleared(self) -> None:
        """Drop every filter and the search text."""
        self.toolbar.search.delete(0, "end")
        self.filters, self.query.search = ActivityFilter(), ""
        self.first_page()

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
        elif ask_confirm(self, self.theme, "Purge activity log",
                         f"Permanently delete {count} entries older than {days} days (the "
                         "retention setting)? The purge itself will be logged.", "Purge",
                         danger=True):
            removed = self.guarded("Activity Log > Purge", activity.purge_expired)
            if removed is not None:
                self.notify(f"Purged {removed} old entries.", "success")
                self.refresh()
