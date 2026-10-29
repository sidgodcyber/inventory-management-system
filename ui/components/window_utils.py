"""Small window helpers shared by dialogs.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

from config.config_loader import AppConfig


def fit_to_screen(window: Any, config: AppConfig) -> None:
    """Size and centre the main window, never larger than the screen.

    Args:
        window: The main ``CTk`` window.
        config: Source of preferred size, minimum size and screen margin.
    """
    max_w = window.winfo_screenwidth() - config.get("ui.screen_margin")
    max_h = window.winfo_screenheight() - config.get("ui.screen_margin")
    width = min(config.get("ui.window_width"), max_w)
    height = min(config.get("ui.window_height"), max_h)
    x, y = (window.winfo_screenwidth() - width) // 2, max((max_h - height) // 2, 0)
    window.geometry(f"{width}x{height}+{x}+{y}")
    window.minsize(min(config.get("ui.min_width"), max_w), min(config.get("ui.min_height"), max_h))


def center_on_parent(window: Any, parent: Any) -> None:
    """Place ``window`` in the middle of ``parent``'s top-level window, on screen.

    Args:
        window: The dialog to position (already populated with widgets).
        parent: Any widget inside the owning window.
    """
    window.update_idletasks()
    owner = parent.winfo_toplevel()
    width, height = window.winfo_reqwidth(), window.winfo_reqheight()
    x = owner.winfo_rootx() + (owner.winfo_width() - width) // 2
    y = owner.winfo_rooty() + (owner.winfo_height() - height) // 2
    x = max(0, min(x, window.winfo_screenwidth() - width))
    y = max(0, min(y, window.winfo_screenheight() - height))
    window.geometry(f"+{x}+{y}")
