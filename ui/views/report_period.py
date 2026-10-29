"""Report period selector: quick 30/90/180-day buttons or custom dates.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date
from typing import Any

import customtkinter as ctk

from utils.date_helpers import days_ago
from utils.validators import Validator

CUSTOM = "Custom"


class PeriodBar(ctk.CTkFrame):
    """Segmented quick periods, two date boxes and a Run button.

    Args:
        master: Parent widget.
        periods: Quick period lengths in days (from config).
        on_run: Called whenever the report should be (re)run.
    """

    def __init__(self, master: Any, periods: Sequence[int], on_run: Callable[[], None]) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_run = on_run
        self._date_format = "%Y-%m-%d"
        self.period = ctk.CTkSegmentedButton(self, values=[*(f"{d} days" for d in periods), CUSTOM],
                                             command=self._chosen)
        self.period.pack(side="left")
        self.date_from = ctk.CTkEntry(self, width=130)
        self.date_from.pack(side="left", padx=(12, 0))
        self.date_to = ctk.CTkEntry(self, width=130)
        self.date_to.pack(side="left", padx=(6, 0))
        ctk.CTkButton(self, text="Run report", width=110, command=on_run).pack(side="left",
                                                                               padx=(8, 0))

    def preset(self, start: date, end: date, date_format: str) -> None:
        """Fill the boxes with a period and select the matching quick button.

        Args:
            start: First day.
            end: Last day.
            date_format: ``strftime`` pattern from settings.
        """
        self._date_format = date_format
        label = f"{(end - start).days + 1} days"
        self.period.set(label if label in self.period.cget("values") else CUSTOM)
        self._set_dates(start, end)

    def is_empty(self) -> bool:
        """True until a period has been entered or preset."""
        return not self.date_from.get().strip()

    def read(self, date_format: str, default: tuple[date, date]) -> tuple[date, date]:
        """Validated period from the boxes (a reversed range is swapped).

        Args:
            date_format: ``strftime`` pattern from settings.
            default: Period used for empty boxes.

        Returns:
            ``(start, end)``.

        Raises:
            ValidationError: If a date does not match the format.
        """
        self._date_format = date_format
        start = Validator.date(self.date_from.get(), "From date", date_format) or default[0]
        end = Validator.date(self.date_to.get(), "To date", date_format) or default[1]
        return (start, end) if start <= end else (end, start)

    def _chosen(self, value: str) -> None:
        """Quick period clicked: fill the dates and run."""
        if value != CUSTOM:
            days = int(value.split()[0])
            self._set_dates(days_ago(days - 1), date.today())
            self._on_run()

    def _set_dates(self, start: date, end: date) -> None:
        """Write both dates in the current format."""
        for entry, value in ((self.date_from, start), (self.date_to, end)):
            entry.delete(0, "end")
            entry.insert(0, value.strftime(self._date_format))
