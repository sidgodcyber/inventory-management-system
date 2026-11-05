"""Sign-in screen shown before anything else (and after signing out).

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from core.exceptions import AppError
from models.user import User
from services.container import AppServices
from ui.components.messages import show_error
from ui.theme import Theme


class LoginView(ctk.CTkFrame):
    """Centred card with username, password and a Sign in button.

    Args:
        master: Content area of the main window.
        theme: Shared theme.
        services: Service container (sign-in and error recording).
        on_success: Called with the signed-in user.
        message: Optional note shown above the form (e.g. after signing out).
    """

    def __init__(self, master: Any, theme: Theme, services: AppServices,
                 on_success: Callable[[User], None], message: str = "") -> None:
        super().__init__(master, fg_color="transparent")
        self._services = services
        self._on_success = on_success
        card = ctk.CTkFrame(self, corner_radius=12)
        card.place(relx=0.5, rely=0.45, anchor="center")
        cfg = services.config
        ctk.CTkLabel(card, text=cfg.get("app.name"), font=theme.font(8, "bold")).pack(
            padx=40, pady=(32, 2))
        ctk.CTkLabel(card, text="Sign in to continue", font=theme.font(-1),
                     text_color=theme.color("muted")).pack(pady=(0, 18))
        self.username = ctk.CTkEntry(card, width=280, placeholder_text="Username",
                                     font=theme.font())
        self.password = ctk.CTkEntry(card, width=280, placeholder_text="Password", show="•",
                                     font=theme.font())
        for entry in (self.username, self.password):
            entry.pack(padx=40, pady=5)
            entry.bind("<Return>", lambda _e: self.submit())
        self.error = ctk.CTkLabel(card, text=message, wraplength=280, font=theme.font(-1),
                                  text_color=theme.color("danger"))
        self.error.pack(padx=40, pady=(6, 0))
        ctk.CTkButton(card, text="Sign in", width=280, command=self.submit).pack(
            padx=40, pady=(10, 32))
        self.after(150, self._focus_username)

    def _focus_username(self) -> None:
        """Put the cursor in the username box, unless the form has already closed."""
        if self.winfo_exists():
            self.username.focus_set()

    def submit(self) -> None:
        """Try to sign in; show a friendly message on failure."""
        try:
            user = self._services.auth.login(self.username.get(), self.password.get())
        except AppError as exc:
            self.password.delete(0, "end")
            self.error.configure(text=exc.message)
            return
        except Exception as exc:  # noqa: BLE001 - last line of defence for the UI
            self._services.activity.record_error("Sign in", exc)
            show_error(self, "signing in")
            return
        self._on_success(user)
