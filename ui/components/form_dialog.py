"""Reusable modal form dialog built from a list of field definitions.

Views describe *what* to ask (:class:`FormField` list) and *what to do* with the
answers (an ``on_submit`` callback). This component handles layout, required
markers, inline error display and keyboard shortcuts, so no view repeats form
widget code.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import customtkinter as ctk

from ui.components.window_utils import center_on_parent
from ui.theme import Theme

# Field kinds supported by the dialog.
ENTRY = "entry"
COMBO = "combo"      # drop-down that only allows listed values
TEXT = "text"        # multi-line text

#: ``on_submit(values)`` returns ``None`` on success or an error message to show.
SubmitHandler = Callable[[dict[str, str]], str | None]


@dataclass(frozen=True)
class FormField:
    """One input in a :class:`FormDialog`.

    Attributes:
        key: Key used in the values dictionary.
        label: Text shown to the left of the input.
        kind: ``entry``, ``combo`` or ``text``.
        options: Choices for ``combo`` fields.
        required: Show a required marker (validation itself happens in services).
        placeholder: Hint shown in empty entries.
        hint: Small help text under the input.
    """

    key: str
    label: str
    kind: str = ENTRY
    options: Sequence[str] = ()
    required: bool = False
    placeholder: str = ""
    hint: str = ""


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
        widget = self._make_input(frame, field, "" if value is None else str(value))
        widget.grid(row=row, column=1, sticky="ew", pady=6)
        self._inputs[field.key] = widget
        if field.hint:
            row += 1
            ctk.CTkLabel(frame, text=field.hint, font=self._theme.font(-2),
                         text_color=self._theme.color("muted")).grid(
                row=row, column=1, sticky="w", pady=(0, 4))
        return row + 1

    def _make_input(self, frame: Any, field: FormField, value: str) -> Any:
        """Create the widget for one field kind, pre-filled with ``value``."""
        if field.kind == COMBO:
            widget = ctk.CTkOptionMenu(frame, values=list(field.options) or [""], width=300,
                                       dynamic_resizing=False, font=self._theme.font())
            widget.set(value if value in field.options else (field.options[0]
                                                             if field.options else ""))
            return widget
        if field.kind == TEXT:
            widget = ctk.CTkTextbox(frame, width=300, height=80, font=self._theme.font())
            widget.insert("1.0", value)
            return widget
        widget = ctk.CTkEntry(frame, width=300, placeholder_text=field.placeholder,
                              font=self._theme.font())
        if value:
            widget.insert(0, value)
        return widget

    def _build_buttons(self, frame: Any, row: int, submit_text: str) -> None:
        """Primary and cancel buttons."""
        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.grid(row=row, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ctk.CTkButton(buttons, text="Cancel", width=100, fg_color="transparent",
                      border_width=1, text_color=("gray10", "gray90"),
                      command=self.destroy).pack(side="right")
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
        """Current text of every input, keyed by field key."""
        result: dict[str, str] = {}
        for key, widget in self._inputs.items():
            if isinstance(widget, ctk.CTkTextbox):
                result[key] = widget.get("1.0", "end").strip()
            else:
                result[key] = widget.get().strip()
        return result

    def _submit(self) -> None:
        """Hand values to the owner; close on success, otherwise show the error."""
        error = self._on_submit(self.values())
        if error:
            self._error.configure(text=f"⚠ {error}")
        else:
            self.grab_release()
            self.destroy()
