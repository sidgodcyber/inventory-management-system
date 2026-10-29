"""Main window: sidebar, content area, status bar, live settings and error hook.

Screens (see :mod:`ui.navigation`) are created lazily the first time they are
opened and then cached. Runtime setting changes are broadcast here: the
appearance mode re-themes the UI, the operator name updates the status bar,
and display settings refresh the visible screen.

Layer: ui
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from config.config_loader import PROJECT_ROOT
from services.container import AppServices
from ui.components.messages import show_error
from ui.components.sidebar import Sidebar
from ui.components.status_bar import StatusBar
from ui.components.window_utils import fit_to_screen
from ui.navigation import BADGE_SCREEN, HOME, NAVIGATION, VIEW_CLASSES
from ui.theme import Theme
from ui.views.base_view import BaseView


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
        self.title(f"{self.config_data.get('app.name')} · v{self.config_data.get('app.version')}")
        fit_to_screen(self, self.config_data)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.theme.style_tables()
        self._build_layout()
        services.settings.subscribe(self._on_setting_changed)
        self.update_status_info()
        self.refresh_badge()
        self.show(HOME)

    def _build_layout(self) -> None:
        """Sidebar, content area and status bar."""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        cfg = self.config_data
        self.sidebar = Sidebar(self, self.theme, cfg.get("app.short_name"), cfg.get("app.tagline"),
                               cfg.get("ui.sidebar_width"), NAVIGATION, self.show)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=24, pady=(20, 12))
        self.status = StatusBar(self, self.theme, cfg.get("ui.toast_ms"))
        self.status.grid(row=1, column=0, columnspan=2, sticky="ew")

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
        self.sidebar.highlight(key)
        view.on_show()

    # -- shared state -----------------------------------------------------------------
    def refresh_badge(self) -> None:
        """Update the low-stock count badge (called after any stock change)."""
        self.sidebar.set_badge(BADGE_SCREEN, self.services.products.low_stock_count())

    def update_status_info(self) -> None:
        """Show operator, role, database path and version in the status bar."""
        settings = self.services.settings
        db_path = self.services.db.path
        try:
            db_path = str(PROJECT_ROOT.joinpath(db_path).relative_to(PROJECT_ROOT))
        except ValueError:
            pass  # database outside the project folder: show the full path
        self.status.set_info(
            f"Operator: {settings.get('operator_name')} ({settings.get('operator_role')})"
            f"   ·   DB: {db_path}   ·   v{self.config_data.get('app.version')}")

    def _on_setting_changed(self, key: str, value: Any) -> None:
        """Apply a saved setting immediately (no restart needed)."""
        if key == "appearance_mode":
            self.theme.apply_appearance(value)
        if key in ("operator_name", "operator_role"):
            self.update_status_info()
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
        """Close the window, then the database."""
        self.destroy()
        self.services.db.close()
