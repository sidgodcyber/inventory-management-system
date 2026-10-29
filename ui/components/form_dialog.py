"""Reusable modal form dialog built from a list of field definitions.

Views describe *what* to ask (a list of
:class:`~ui.components.form_fields.FormField`) and *what to do* with the
answers (an ``on_submit`` callback). This component handles layout, required
markers, inline error display and keyboard shortcuts, so no view repeats form
widget code.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import customtkinter as ctk

from ui.components.form_fields import COMBO, ENTRY, TEXT, FormField, make_input, read_input
from ui.components.window_utils import center_on_parent
from ui.theme import Theme

__all__ = ["COMBO", "ENTRY", "TEXT", "FormDialog", "FormField", "SubmitHandler"]

#: ``on_submit(values)`` returns ``None`` on success or an error message to show.
SubmitHandler = Callable[[dict[str, str]], str | None]


class FormDialog(ctk.CTkToplevel):
    """Modal dialog that collects values for a list of fields.

    Args:
        master: Parent window.
        theme: Shared theme.
        title: Window title and heading.
        fields: Inputs to show, in order.
        on_submit: Called with the values; return an error message to keep the
            dialog open, or ``None`` to close it.
        initial: Initial values by field key.
        submit_text: Label of the primary button.
    """

    def __init__(self, master: Any, theme: Theme, title: str, fields: Sequence[FormField],
                 on_submit: SubmitHandler, initial: Mapping[str, Any] | None = None,
                 submit_text: str = "Save") -> None:
        super().__init__(master)
        self._theme = theme
        self._fields = list(fields)
        self._on_submit = on_submit
        self._inputs: dict[str, Any] = {}
        self.title(title)
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self._build(title, initial or {}, submit_text)
        center_on_parent(self, master)
        self.bind("<Escape>", lambda _e: self.destroy())
        # CTkToplevel needs a moment to map before it can grab focus on Windows.
        self.after(120, self._activate)

    # -- layout ---------------------------------------------------------------------
    def _build(self, title: str, initial: Mapping[str, Any], submit_text: str) -> None:
        """Create heading, inputs, error label and buttons."""
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=20)
        ctk.CTkLabel(frame, text=title, font=self._theme.font(4, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))
        row = 1
        for field in self._fields:
            row = self._add_field(frame, field, initial.get(field.key), row)
        self._error = ctk.CTkLabel(frame, text="", text_color=self._theme.color("danger"),
                                   wraplength=420, justify="left", font=self._theme.font(-1))
        self._error.grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self._build_buttons(frame, row + 1, submit_text)

    def _add_field(self, frame: Any, field: FormField, value: Any, row: int) -> int:
        """Place one labelled input; return the next free grid row."""
        label = f"{field.label}{' *' if field.required else ''}"
        ctk.CTkLabel(frame, text=label, font=self._theme.font()).grid(
            row=row, column=0, sticky="nw", padx=(0, 16), pady=6)
        widget = make_input(frame, field, "" if value is None else str(value), self._theme)
        widget.grid(row=row, column=1, sticky="ew", pady=6)
        self._inputs[field.key] = widget
        if field.hint:
            row += 1
            ctk.CTkLabel(frame, text=field.hint, font=self._theme.font(-2),
                         text_color=self._theme.color("muted")).grid(
                row=row, column=1, sticky="w", pady=(0, 4))
        return row + 1

    def _build_buttons(self, frame: Any, row: int, submit_text: str) -> None:
        """Primary and cancel buttons."""
        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.grid(row=row, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ctk.CTkButton(buttons, text="Cancel", width=100, command=self.destroy,
                      **self._theme.button_style("secondary")).pack(side="right")
        ctk.CTkButton(buttons, text=submit_text, width=120,
                      command=self._submit).pack(side="right", padx=(0, 8))
        self.bind("<Control-Return>", lambda _e: self._submit())

    def _activate(self) -> None:
        """Bring the dialog to the front, make it modal and focus the first input."""
        self.lift()
        self.focus_force()
        self.grab_set()
        first = next(iter(self._inputs.values()), None)
        if first is not None:
            first.focus_set()

    # -- values ---------------------------------------------------------------------
    def values(self) -> dict[str, str]:
        """Current text of every input.

        Returns:
            ``{field key: trimmed text}``.
        """
        return {key: read_input(widget) for key, widget in self._inputs.items()}

    def _submit(self) -> None:
        """Hand values to the owner; close on success, otherwise show the error."""
        error = self._on_submit(self.values())
        if error:
            self._error.configure(text=f"⚠ {error}")
        else:
            self.grab_release()
            self.destroy()
