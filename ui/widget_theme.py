"""CustomTkinter widget colours, generated from the config palette.

The chrome holds no colour: controls are neutral, the one primary action is
near-black (inverted on dark), and hue is left for data and status. Overriding
the theme here means every widget follows the palette without each view
having to say so.

Layer: ui
Author: Siddhi Baluja
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

_CONTROL_RADIUS = 6
_CARD_RADIUS = 8


def widget_colors(pair: Any) -> dict[str, dict[str, Any]]:
    """Theme overrides for each CustomTkinter widget.

    Args:
        pair: Function returning the ``(light, dark)`` colours of a palette name.

    Returns:
        ``{widget name: {option: value}}`` to merge into the loaded theme.
    """
    ground, surface, raised = pair("ground"), pair("surface"), pair("raised")
    text, muted, control = pair("text"), pair("muted"), pair("control")
    primary, hover = pair("primary"), pair("primary_hover")
    field = {"fg_color": surface, "border_color": control, "border_width": 1,
             "corner_radius": _CONTROL_RADIUS, "text_color": text}
    menu = {"fg_color": raised, "button_color": raised, "button_hover_color": control,
            "corner_radius": _CONTROL_RADIUS, "text_color": text, "text_color_disabled": muted}
    return {
        "CTk": {"fg_color": ground},
        "CTkToplevel": {"fg_color": ground},
        "CTkFrame": {"fg_color": surface, "top_fg_color": surface, "corner_radius": _CARD_RADIUS},
        "CTkLabel": {"text_color": text},
        "CTkButton": {"fg_color": primary, "hover_color": hover, "text_color": pair("primary_text"),
                      "text_color_disabled": muted, "corner_radius": _CONTROL_RADIUS,
                      "border_width": 0},
        "CTkEntry": {**field, "placeholder_text_color": muted},
        "CTkOptionMenu": menu,
        "CTkComboBox": {**field, "button_color": raised, "button_hover_color": control,
                        "text_color_disabled": muted},
        "CTkCheckBox": {"fg_color": primary, "hover_color": hover, "border_color": control,
                        "checkmark_color": pair("primary_text"), "text_color": text,
                        "corner_radius": 4, "border_width": 2},
        "CTkSegmentedButton": {"fg_color": raised, "selected_color": surface,
                               "selected_hover_color": surface, "unselected_color": raised,
                               "unselected_hover_color": control, "text_color": text,
                               "text_color_disabled": muted, "corner_radius": _CONTROL_RADIUS},
        "CTkScrollbar": {"fg_color": "transparent", "button_color": control,
                         "button_hover_color": muted},
        "CTkTextbox": {"fg_color": surface, "border_color": pair("border"), "border_width": 1,
                       "corner_radius": _CARD_RADIUS, "text_color": text,
                       "scrollbar_button_color": control, "scrollbar_button_hover_color": muted},
        "CTkScrollableFrame": {"label_fg_color": raised},
        "CTkProgressBar": {"fg_color": raised, "progress_color": pair("hue"), "corner_radius": 3},
        "DropdownMenu": {"fg_color": surface, "hover_color": raised, "text_color": text},
    }


def install_widget_theme(base_theme: str, pair: Any) -> None:
    """Load a built-in theme and apply the palette (before any widget exists).

    Args:
        base_theme: CustomTkinter theme supplying metrics such as fonts.
        pair: Function returning the ``(light, dark)`` colours of a palette name.
    """
    ctk.set_default_color_theme(base_theme)
    for widget, options in widget_colors(pair).items():
        ctk.ThemeManager.theme[widget].update(options)
