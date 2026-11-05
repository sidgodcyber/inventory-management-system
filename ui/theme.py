"""Central look-and-feel: fonts, palette and ttk table styling.

Every colour and font size comes from ``config.json`` (``ui`` section). Light/dark
variants are stored as ``<name>_light`` / ``<name>_dark`` keys and resolved here,
so no view ever hard-codes a colour.

Layer: ui
Author: Siddhi Baluja
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
        self.strong_family: str = config.get("ui.strong_font_family")
        self.control_height: int = config.get("ui.control_height")
        self.size: int = config.get("ui.font_size")
        self.heading_size: int = config.get("ui.heading_size")
        self._fonts: dict[tuple[int, str], ctk.CTkFont] = {}
        self._listeners: list[Callable[[], None]] = []

    # -- fonts ----------------------------------------------------------------------
    def font(self, delta: int = 0, weight: str = "normal") -> ctk.CTkFont:
        """Cached CTkFont ``delta`` points larger than the base size.

        Args:
            delta: Size difference from the base font size.
            weight: ``normal`` or ``bold`` (the semibold face, for titles and lead figures).

        Returns:
            The font.
        """
        key = (self.size + delta, weight)
        if key not in self._fonts:
            family = self.strong_family if weight == "bold" else self.family
            self._fonts[key] = ctk.CTkFont(family=family, size=key[0])
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

    def color(self, name: str) -> tuple[str, str]:
        """A palette colour in the ``(light, dark)`` form CustomTkinter widgets accept."""
        return self.pair(name)

    def mode_color(self, base: str) -> str:
        """The ``<base>_light`` or ``<base>_dark`` colour for the current mode.

        For Tk and Matplotlib, which cannot follow the appearance mode by themselves.
        """
        return self.palette[f"{base}_{'dark' if self.is_dark() else 'light'}"]

    def button_style(self, kind: str = "primary") -> dict[str, object]:
        """Keyword options for a CTkButton of the given kind.

        Args:
            kind: ``primary`` (near-black, one per screen), ``secondary`` (a grey fill)
                or ``danger`` (outlined in the negative colour).

        Returns:
            Options to pass as ``**style`` to ``ctk.CTkButton``.
        """
        if kind == "secondary":
            return {"fg_color": self.pair("raised"), "hover_color": self.pair("control"),
                    "text_color": self.pair("text")}
        if kind == "danger":
            return {"fg_color": "transparent", "border_width": 1, "hover_color": self.pair("raised"),
                    "border_color": self.pair("danger"), "text_color": self.pair("danger")}
        return {}

    def card_style(self) -> dict[str, object]:
        """Options for a card: a white sheet with a 1px edge, flat, no shadow.

        Returns:
            Options to pass as ``**style`` to ``ctk.CTkFrame``.
        """
        return {"fg_color": self.pair("surface"), "border_width": 1,
                "border_color": self.pair("border"), "corner_radius": 8}

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
        background = self.mode_color("surface")
        foreground = self.mode_color("text")
        style.layout(TABLE_STYLE, [("Treeview.treearea", {"sticky": "nswe"})])  # no outer frame
        style.configure(TABLE_STYLE, background=background, fieldbackground=background,
                        foreground=foreground, rowheight=self.config.get("ui.table_row_height"),
                        font=self.tk_font(-1), borderwidth=0)
        # No header band: 12px grey sentence-case labels on the table's own surface.
        style.configure(f"{TABLE_STYLE}.Heading", background=background, relief="flat",
                        foreground=self.mode_color("muted"), font=self.tk_font(-2), padding=(6, 6),
                        borderwidth=0, bordercolor=background, lightcolor=background,
                        darkcolor=background)
        style.map(TABLE_STYLE, background=[("selected", self.mode_color("selection_bg"))],
                  foreground=[("selected", foreground)])
        style.map(f"{TABLE_STYLE}.Heading", background=[("active", background)],
                  foreground=[("active", foreground)])
