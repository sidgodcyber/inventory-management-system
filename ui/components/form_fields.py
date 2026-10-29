"""Form field definitions and the widget factory used by :mod:`form_dialog`.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import customtkinter as ctk

from ui.theme import Theme

# Field kinds supported by the form dialog.
ENTRY = "entry"
COMBO = "combo"      # drop-down that only allows listed values
TEXT = "text"        # multi-line text
_INPUT_WIDTH = 300


@dataclass(frozen=True)
class FormField:
    """One input in a form dialog.

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


def make_input(master: Any, field: FormField, value: str, theme: Theme) -> Any:
    """Create the widget for a field, pre-filled with ``value``.

    Args:
        master: Parent widget.
        field: Field definition.
        value: Initial text.
        theme: Shared theme (fonts).

    Returns:
        A ``CTkOptionMenu``, ``CTkTextbox`` or ``CTkEntry``.
    """
    if field.kind == COMBO:
        options = list(field.options) or [""]
        widget = ctk.CTkOptionMenu(master, values=options, width=_INPUT_WIDTH,
                                   dynamic_resizing=False, font=theme.font())
        widget.set(value if value in options else options[0])
        return widget
    if field.kind == TEXT:
        widget = ctk.CTkTextbox(master, width=_INPUT_WIDTH, height=80, font=theme.font())
        widget.insert("1.0", value)
        return widget
    widget = ctk.CTkEntry(master, width=_INPUT_WIDTH, placeholder_text=field.placeholder,
                          font=theme.font())
    if value:
        widget.insert(0, value)
    return widget


def read_input(widget: Any) -> str:
    """Current text of any widget created by :func:`make_input`.

    Args:
        widget: The input widget.

    Returns:
        Its trimmed text.
    """
    if isinstance(widget, ctk.CTkTextbox):
        return widget.get("1.0", "end").strip()
    return widget.get().strip()
