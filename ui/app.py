"""Main window: sign-in, role-aware sidebar, content area, status bar and live settings.

The window opens on the sign-in screen. After a successful sign-in (and a
forced password change when required) it builds a sidebar containing only the
screens the user's role may open. Signing out discards every screen, so the
next user never sees the previous user's data or buttons.

Layer: ui
Author: Siddhi Baluja
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from models.user import User
from services.container import AppServices
from ui.components.messages import show_error
from ui.components.sidebar import Sidebar
from ui.components.status_bar import StatusBar
from ui.components.window_utils import fit_to_screen
from ui.navigation import HOME, VIEW_CLASSES
from ui.session import build_sidebar, destroy_widgets, refresh_badge, status_text
from ui.theme import Theme
from ui.views.base_view import BaseView
from ui.views.change_password import ask_new_password
from ui.views.login import LoginView

_MUST_CHANGE = "You must set a new password before using the system."


class App(ctk.CTk):
    """The application window.

    Args:
        services: Fully wired service container.
    """

    def __init__(self, services: AppServices) -> None:
        self.services = services
        self.config_data = services.config
        self.theme = Theme(services.config)
        # Appearance and colour theme must be set before any widget is created.
        ctk.set_appearance_mode(services.settings.get("appearance_mode"))
        ctk.set_default_color_theme(services.config.get("ui.color_theme"))
        super().__init__()
        self._views: dict[str, BaseView] = {}
        self._current: str | None = None
        self.sidebar: Sidebar | None = None
        self._login: LoginView | None = None
        self.title(f"{self.config_data.get('app.name')} · v{self.config_data.get('app.version')}")
        fit_to_screen(self, self.config_data)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.theme.style_tables()
        self._build_layout()
        services.settings.subscribe(self._on_setting_changed)
        self.show_login()

    def _build_layout(self) -> None:
        """Create the content area and status bar.

        The sidebar is added only after sign-in, because its entries depend on
        the signed-in user's role.
        """
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=24, pady=(20, 12))
        self.status = StatusBar(self, self.theme, self.config_data.get("ui.toast_ms"))
        self.status.grid(row=1, column=0, columnspan=2, sticky="ew")

    # -- session ----------------------------------------------------------------------
    def show_login(self, message: str = "") -> None:
        """Clear the session's screens and show the sign-in form.

        Args:
            message: Optional note shown on the form (e.g. why the user was signed out).
        """
        self._discard_session_widgets()
        self._login = LoginView(self.content, self.theme, self.services, self._signed_in, message)
        self._login.pack(fill="both", expand=True)
        self.update_status_info()

    def _signed_in(self, user: User) -> None:
        """Finish signing in.

        A user flagged to change their password (first sign-in or after an
        admin reset) must do so now; cancelling signs them out again. Otherwise
        the role-filtered sidebar is built and the home screen opens.

        Args:
            user: The user who just signed in.
        """
        if user.must_change_password and not ask_new_password(self, self.theme, self.services,
                                                              forced=True):
            self.sign_out(_MUST_CHANGE)
            return
        self._login.destroy()
        self._login = None
        self.sidebar = build_sidebar(self, self.theme, self.services, self.show,
                                     self.change_password, self.sign_out)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.update_status_info()
        self.refresh_badge()
        self.show(HOME)

    def change_password(self) -> None:
        """Let the signed-in user choose a new password."""
        if ask_new_password(self, self.theme, self.services, forced=False):
            self.status.show("Password changed.", "success")

    def sign_out(self, message: str = "") -> None:
        """End the session and return to the sign-in screen.

        Args:
            message: Optional note shown on the sign-in form.
        """
        self.services.auth.logout()
        self.show_login(message)

    def _discard_session_widgets(self) -> None:
        """Destroy every screen and the sidebar so nothing leaks to the next user.

        Screens are rebuilt on demand for the next session, so they pick up
        that user's permissions (hidden buttons, filtered navigation).
        """
        destroy_widgets(self._views, self.sidebar, self._login)
        self._current = None
        self.sidebar = self._login = None

    # -- navigation -------------------------------------------------------------------
    def view(self, key: str) -> BaseView:
        """Return the screen for ``key``, creating it on first use.

        Args:
            key: Screen key from :data:`ui.navigation.VIEW_CLASSES`.

        Returns:
            The cached view instance.
        """
        if key not in self._views:
            self._views[key] = VIEW_CLASSES[key](self.content, self)
        return self._views[key]

    def show(self, key: str) -> None:
        """Display a screen and refresh its data.

        Args:
            key: Screen key from :data:`ui.navigation.VIEW_CLASSES`.
        """
        if self._current in self._views:
            self._views[self._current].pack_forget()
        view = self.view(key)
        view.pack(fill="both", expand=True)
        self._current = key
        if self.sidebar is not None:
            self.sidebar.highlight(key)
        view.on_show()

    # -- shared state -----------------------------------------------------------------
    def refresh_badge(self) -> None:
        """Update the low-stock count badge (called after any stock change)."""
        refresh_badge(self.sidebar, self.services)

    def update_status_info(self) -> None:
        """Show the signed-in user, database path and version in the status bar."""
        self.status.set_info(status_text(self.services))

    def _on_setting_changed(self, key: str, value: Any) -> None:
        """Apply a saved setting immediately (no restart needed).

        Args:
            key: Changed setting.
            value: Its new value.
        """
        if key == "appearance_mode":
            self.theme.apply_appearance(value)
        current = self._views.get(self._current or "")
        if current is not None:
            current.on_setting_changed(key, value)

    # -- errors and shutdown ----------------------------------------------------------
    def report_callback_exception(self, exc: type[BaseException], val: BaseException,
                                  tb: Any) -> None:
        """Tk hook for exceptions escaping any callback: record and apologise.

        Args:
            exc: Exception class.
            val: Exception instance (recorded as an ``ERROR`` activity entry).
            tb: Traceback (kept in the activity entry, never shown to the user).
        """
        self.services.activity.record_error("UI callback", val)
        show_error(self, "handling that action")

    def destroy(self) -> None:
        """Detach from settings notifications, then destroy the window."""
        self.services.settings.unsubscribe(self._on_setting_changed)
        super().destroy()

    def _on_close(self) -> None:
        """Sign out (logged), close the window, then the database."""
        self.services.auth.logout()
        self.destroy()
        self.services.db.close()
