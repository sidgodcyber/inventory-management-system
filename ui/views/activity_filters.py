"""Filter row for the Activity Log: date range, action, entity and user.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from models.filters import ActivityFilter
from ui.theme import Theme
from utils.validators import Validator

ANY = "All"


class ActivityFilterBar(ctk.CTkFrame):
    """Labelled filter inputs with Apply and Clear buttons.

    Args:
        master: Parent widget.
        theme: Shared theme.
        on_apply: Called when Apply is pressed.
        on_clear: Called after the inputs are reset.
    """

    def __init__(self, master: Any, theme: Theme, on_apply: Callable[[], None],
                 on_clear: Callable[[], None]) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_clear = on_clear
        self.date_from = ctk.CTkEntry(self, width=130)
        self.date_to = ctk.CTkEntry(self, width=130)
        self.action = ctk.CTkOptionMenu(self, values=[ANY], width=145)
        self.entity = ctk.CTkOptionMenu(self, values=[ANY], width=130)
        self.user = ctk.CTkOptionMenu(self, values=[ANY], width=120)
        for label, widget in (("From", self.date_from), ("To", self.date_to),
                              ("Action", self.action), ("Entity", self.entity),
                              ("User", self.user)):
            ctk.CTkLabel(self, text=label, font=theme.font(-1)).pack(side="left", padx=(0, 4))
            widget.pack(side="left", padx=(0, 10))
        ctk.CTkButton(self, text="Clear", width=70, command=self.clear,
                      **theme.button_style("secondary")).pack(side="right")
        ctk.CTkButton(self, text="Apply", width=70, command=on_apply).pack(side="right",
                                                                          padx=(0, 6))

    def set_options(self, options: dict[str, list[str]], example_date: str) -> None:
        """Fill the drop-downs and show an example date.

        Args:
            options: ``actions``, ``entities`` and ``users`` lists from the service.
            example_date: Today's date in the configured format.
        """
        self.action.configure(values=[ANY, *options["actions"]])
        self.entity.configure(values=[ANY, *options["entities"]])
        self.user.configure(values=[ANY, *options["users"]])
        for entry in (self.date_from, self.date_to):
            entry.configure(placeholder_text=f"e.g. {example_date}")

    def read(self, date_format: str) -> ActivityFilter:
        """Build a filter from the inputs.

        Args:
            date_format: ``strftime`` pattern for the date boxes.

        Returns:
            The activity filter (``All`` means no restriction).

        Raises:
            ValidationError: If a date does not match the format.
        """
        def pick(menu: ctk.CTkOptionMenu) -> str | None:
            """Selected value, or ``None`` for "All"."""
            return None if menu.get() == ANY else menu.get()

        return ActivityFilter(
            date_from=Validator.date(self.date_from.get(), "From date", date_format),
            date_to=Validator.date(self.date_to.get(), "To date", date_format),
            action=pick(self.action), entity=pick(self.entity), user=pick(self.user))

    def clear(self) -> None:
        """Reset every input and notify the owner."""
        for entry in (self.date_from, self.date_to):
            entry.delete(0, "end")
        for menu in (self.action, self.entity, self.user):
            menu.set(ANY)
        self._on_clear()
