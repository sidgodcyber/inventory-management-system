"""Sidebar on the page ground: product mark, one row per screen and the account footer.

The chrome holds no colour. The active screen is a neutral grey pill, and the
only colour is the product's mark and the count on a queue that needs action.

Layer: ui/components
Author: Siddhi Baluja
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import customtkinter as ctk

from ui.theme import Theme

_MARK_BARS = (22, 16, 9)  # three shelves of stock running down


def product_mark(master: Any, theme: Theme) -> ctk.CTkFrame:
    """The product's mark: a shelf of stock running down towards its reorder level.

    Args:
        master: Parent widget.
        theme: Shared theme.

    Returns:
        A small frame holding the mark.
    """
    mark = ctk.CTkFrame(master, fg_color="transparent", width=24, height=24)
    for width in _MARK_BARS:
        ctk.CTkFrame(mark, width=width, height=5, corner_radius=1,
                     fg_color=theme.pair("hue")).pack(anchor="w", pady=1)
    return mark


class Sidebar(ctk.CTkFrame):
    """Vertical navigation panel.

    Args:
        master: Main window.
        theme: Shared theme.
        title: Short application name shown at the top.
        caption: Small text under the title.
        width: Sidebar width in pixels (from config).
        entries: ``(screen key, label)`` pairs in display order.
        on_select: Called with the screen key when a button is clicked.
    """

    def __init__(self, master: Any, theme: Theme, title: str, caption: str, width: int,
                 entries: Sequence[tuple[str, str]], on_select: Callable[[str], None]) -> None:
        super().__init__(master, width=width, corner_radius=0, fg_color=theme.pair("ground"))
        self._theme = theme
        self.pack_propagate(False)
        ctk.CTkFrame(self, width=1, corner_radius=0, fg_color=theme.pair("border")).pack(
            side="right", fill="y")
        self._build_brand(title, caption)
        self._buttons = {key: self._button(key, label, on_select) for key, label in entries}
        self._badge: ctk.CTkLabel | None = None

    def _build_brand(self, title: str, caption: str) -> None:
        """The product's mark and name at the top."""
        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.pack(fill="x", padx=20, pady=(22, 18))
        product_mark(brand, self._theme).pack(side="left", padx=(0, 10))
        text = ctk.CTkFrame(brand, fg_color="transparent")
        text.pack(side="left")
        ctk.CTkLabel(text, text=title, height=20, anchor="w",
                     font=self._theme.font(2, "bold")).pack(fill="x")
        ctk.CTkLabel(text, text=caption, height=16, anchor="w", font=self._theme.font(-2),
                     text_color=self._theme.color("muted")).pack(fill="x")

    def _button(self, key: str, label: str, on_select: Callable[[str], None]) -> ctk.CTkButton:
        """One flat navigation row."""
        button = ctk.CTkButton(self, text=label, anchor="w", height=34, fg_color="transparent",
                               text_color=self._theme.pair("text"), font=self._theme.font(),
                               hover_color=self._theme.pair("raised"),
                               command=lambda: on_select(key))
        button.pack(fill="x", padx=12, pady=1)
        return button

    def highlight(self, key: str) -> None:
        """Mark the button of the visible screen with the neutral pill.

        Args:
            key: Screen key currently shown.
        """
        for name, button in self._buttons.items():
            active = self._theme.pair("selection_bg") if name == key else "transparent"
            button.configure(fg_color=active)

    def add_account_footer(self, text: str, on_change_password: Callable[[], None],
                           on_sign_out: Callable[[], None]) -> None:
        """Show who is signed in, with "Change password" and "Sign out" at the bottom.

        Args:
            text: Signed-in user and role.
            on_change_password: Called when "Change password" is clicked.
            on_sign_out: Called when "Sign out" is clicked.
        """
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=12, pady=12)
        ctk.CTkLabel(footer, text=text, font=self._theme.font(-2), justify="left", anchor="w",
                     text_color=self._theme.color("muted")).pack(fill="x", padx=8, pady=(0, 6))
        for label, command in (("Change password", on_change_password),
                               ("Sign out", on_sign_out)):
            ctk.CTkButton(footer, text=label, height=30, command=command, anchor="w",
                          fg_color="transparent", hover_color=self._theme.pair("raised"),
                          text_color=self._theme.pair("text"), font=self._theme.font(-1)).pack(
                fill="x")

    def set_badge(self, key: str, count: int) -> None:
        """Show how many products are low, on a button (hidden when zero).

        Args:
            key: Screen key whose button gets the badge.
            count: Number of products at or below their reorder level.
        """
        if self._badge is None:
            self._badge = ctk.CTkLabel(self._buttons[key], text="", height=20, corner_radius=4,
                                       fg_color=self._theme.pair("pill_negative_bg"),
                                       text_color=self._theme.pair("pill_negative_ink"),
                                       font=self._theme.font(-2))
        if count:
            self._badge.configure(text=f" {count} low ")
            self._badge.place(relx=1.0, rely=0.5, x=-8, anchor="e")
        else:
            self._badge.place_forget()
