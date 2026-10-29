"""Friendly message boxes: the UI never shows a raw traceback.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from tkinter import messagebox
from typing import Any

UNEXPECTED_ERROR = (
    "Something went wrong while {context}.\n\n"
    "The problem has been recorded in the Activity Log and logs/app.log. "
    "Please try again; if it keeps happening, report the time shown in the log."
)


def show_warning(master: Any, title: str, message: str) -> None:
    """Show an expected problem (validation, stock rule) in plain words."""
    messagebox.showwarning(title, message, parent=master)


def show_error(master: Any, context: str) -> None:
    """Show a generic apology for an unexpected defect."""
    messagebox.showerror("Unexpected error", UNEXPECTED_ERROR.format(context=context.lower()),
                         parent=master)


def show_info(master: Any, title: str, message: str) -> None:
    """Show an informational message."""
    messagebox.showinfo(title, message, parent=master)
