"""Small window helpers shared by dialogs.

Layer: ui/components
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any


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
