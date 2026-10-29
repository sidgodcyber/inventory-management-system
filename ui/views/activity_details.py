"""Read-only pane showing one activity entry in full (summary plus JSON).

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import json
from typing import Any

import customtkinter as ctk

from models.activity_log import ActivityLog
from ui.theme import Theme
from ui.views.activity_summary import summarize

_HINT = "Select an entry to see its full details (old → new values, error context)."


class ActivityDetails(ctk.CTkTextbox):
    """Text box that renders the selected activity entry.

    Args:
        master: Parent widget.
        theme: Shared theme.
    """

    def __init__(self, master: Any, theme: Theme) -> None:
        super().__init__(master, height=96, font=theme.font(-1), wrap="word")

    def show(self, entry: ActivityLog | None) -> None:
        """Display ``entry`` (or a hint when nothing is selected).

        Args:
            entry: Entry to show, or ``None``.
        """
        text = _HINT if entry is None else (
            f"#{entry.id}  {entry.timestamp}  {entry.user}  {entry.action} {entry.entity} "
            f"{entry.entity_id or ''}\n{summarize(entry.details)}\n\n"
            f"{json.dumps(entry.details, indent=2, ensure_ascii=False)}")
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.insert("1.0", text)
        self.configure(state="disabled")
