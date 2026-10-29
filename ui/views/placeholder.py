"""Temporary screen used while a view is under construction.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import customtkinter as ctk

from ui.views.base_view import BaseView


class PlaceholderView(BaseView):
    """Shows a short "coming soon" note."""

    title = "Coming soon"

    def build(self) -> None:
        """Create the note label."""
        ctk.CTkLabel(self.body, text="This screen is being built.",
                     font=self.theme.font(2)).pack(pady=40)
