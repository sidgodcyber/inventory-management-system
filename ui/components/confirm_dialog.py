"""Reusable modal yes/no confirmation dialog.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ui.components.window_utils import center_on_parent
from ui.theme import Theme


class ConfirmDialog(ctk.CTkToplevel):
    """Ask the operator to confirm a destructive or important action.

    Args:
        master: Parent widget.
        theme: Shared theme.
        title: Window title / heading.
        message: Explanation of what will happen.
        confirm_text: Label of the confirming button.
        danger: Colour the confirm button as destructive.
    """

    def __init__(self, master: Any, theme: Theme, title: str, message: str,
                 confirm_text: str = "Confirm", danger: bool = False) -> None:
        super().__init__(master)
        self.result = False
        self.title(title)
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=20)
        ctk.CTkLabel(frame, text=title, font=theme.font(4, "bold")).pack(anchor="w")
        ctk.CTkLabel(frame, text=message, wraplength=420, justify="left",
                     font=theme.font()).pack(anchor="w", pady=(10, 18))
        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(fill="x")
        ctk.CTkButton(buttons, text="Cancel", width=100, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"), command=self.destroy).pack(side="right")
        color = theme.color("danger") if danger else theme.color("accent")
        ctk.CTkButton(buttons, text=confirm_text, width=120, fg_color=color,
                      command=self._confirm).pack(side="right", padx=(0, 8))
        center_on_parent(self, master)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self._confirm())
        self.after(120, self._activate)

    def _activate(self) -> None:
        """Bring to front and make modal."""
        self.lift()
        self.focus_force()
        self.grab_set()

    def _confirm(self) -> None:
        """Record the confirmation and close."""
        self.result = True
        self.destroy()


def ask_confirm(master: Any, theme: Theme, title: str, message: str,
                confirm_text: str = "Confirm", danger: bool = False) -> bool:
    """Show a :class:`ConfirmDialog` and wait for the answer.

    Returns:
        ``True`` if the operator confirmed.
    """
    dialog = ConfirmDialog(master, theme, title, message, confirm_text, danger)
    master.wait_window(dialog)
    return dialog.result
