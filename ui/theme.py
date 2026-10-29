"""Central look-and-feel: fonts, palette and ttk table styling.

Every colour and font size comes from ``config.json`` (``ui`` section). Light/dark
variants are stored as ``<name>_light`` / ``<name>_dark`` keys and resolved here,
so no view ever hard-codes a colour.

Layer: ui
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable
from tkinter import ttk

import customtkinter as ctk

from config.config_loader import AppConfig

TABLE_STYLE = "IMS.Treeview"


class Theme:
    """Fonts, colours and theme switching for the whole UI.

    Args:
        config: Source of fonts, sizes and the colour palette.
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.palette: dict[str, str] = config.get("ui.palette")
        self.family: str = config.get("ui.font_family")
        self.size: int = config.get("ui.font_size")
        self.heading_size: int = config.get("ui.heading_size")
        self._fonts: dict[tuple[int, str], ctk.CTkFont] = {}
        self._listeners: list[Callable[[], None]] = []

    # -- fonts ----------------------------------------------------------------------
    def font(self, delta: int = 0, weight: str = "normal") -> ctk.CTkFont:
        """Cached CTkFont ``delta`` points larger than the base size."""
        key = (self.size + delta, weight)
        if key not in self._fonts:
            self._fonts[key] = ctk.CTkFont(family=self.family, size=key[0], weight=weight)
        return self._fonts[key]

    def mono_font(self, delta: int = -1) -> ctk.CTkFont:
        """Monospace font (diagrams, code-like text)."""
        key = (self.size + delta, "mono")
        if key not in self._fonts:
            self._fonts[key] = ctk.CTkFont(family=self.config.get("ui.mono_font_family"),
                                           size=key[0])
        return self._fonts[key]

    def heading_font(self) -> ctk.CTkFont:
        """Font for page titles."""
        return self.font(self.heading_size - self.size, "bold")

    def tk_font(self, delta: int = 0, weight: str = "normal") -> tuple[str, int, str]:
        """Plain Tk font tuple (for ttk widgets that cannot use CTkFont).

        Tk reads a negative size as pixels, matching CustomTkinter's sizing.
        """
        return (self.family, -(self.size + delta), weight)

    # -- colours --------------------------------------------------------------------
    @staticmethod
    def is_dark() -> bool:
        """True when CustomTkinter currently renders in dark mode."""
        return ctk.get_appearance_mode().lower() == "dark"

    def color(self, name: str) -> str:
        """A palette colour that has no light/dark variant (e.g. ``danger``)."""
        return self.palette[name]

    def mode_color(self, base: str) -> str:
        """The ``<base>_light`` or ``<base>_dark`` colour for the current mode."""
        return self.palette[f"{base}_{'dark' if self.is_dark() else 'light'}"]

    def pair(self, base: str) -> tuple[str, str]:
        """``(light, dark)`` colours, the form CustomTkinter widgets accept."""
        return self.palette[f"{base}_light"], self.palette[f"{base}_dark"]

    # -- switching ------------------------------------------------------------------
    def apply_appearance(self, mode: str) -> None:
        """Switch light/dark/system mode and restyle non-CTk widgets.

        Args:
            mode: ``light``, ``dark`` or ``system``.
        """
        ctk.set_appearance_mode(mode)
        self.style_tables()
        for listener in list(self._listeners):
            listener()

    def on_change(self, listener: Callable[[], None]) -> None:
        """Run ``listener()`` after every appearance change (charts, table tags)."""
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        """Stop notifying ``listener``."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def style_tables(self) -> None:
        """Apply the palette to every ``ttk.Treeview`` using :data:`TABLE_STYLE`."""
        style = ttk.Style()
        style.theme_use("clam")
        background = self.mode_color("table_bg")
        foreground = self.mode_color("table_fg")
        style.configure(TABLE_STYLE, background=background, fieldbackground=background,
                        foreground=foreground, rowheight=self.config.get("ui.table_row_height"),
                        font=self.tk_font(), borderwidth=0)
        style.configure(f"{TABLE_STYLE}.Heading", background=self.mode_color("heading_bg"),
                        foreground=foreground, font=self.tk_font(0, "bold"), relief="flat")
        style.map(TABLE_STYLE, background=[("selected", self.color("selection_bg"))],
                  foreground=[("selected", self.color("selection_fg"))])
        style.map(f"{TABLE_STYLE}.Heading",
                  background=[("active", self.mode_color("heading_bg"))])
