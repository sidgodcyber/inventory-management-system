"""Main window: sidebar navigation, content area, status bar and theming.

The window is the only object that knows every screen. Screens are created
lazily the first time they are opened and then cached. Runtime setting
changes are broadcast here: appearance mode re-themes the UI, the operator
name updates the status bar, and display settings refresh the visible screen.

Layer: ui
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from config.config_loader import PROJECT_ROOT
from services.container import AppServices
from ui.components.messages import show_error
from ui.components.status_bar import StatusBar
from ui.theme import Theme
from ui.views.base_view import BaseView
from ui.views.categories import CategoriesView
from ui.views.placeholder import PlaceholderView
from ui.views.products import ProductsView
from ui.views.suppliers import SuppliersView

# Sidebar entries: (key, label). The view class for each key is in VIEW_CLASSES.
NAVIGATION: tuple[tuple[str, str], ...] = (
    ("dashboard", "Dashboard"),
    ("products", "Products"),
    ("categories", "Categories"),
    ("suppliers", "Suppliers"),
    ("stock", "Stock"),
    ("reports", "Reports"),
    ("activity", "Activity Log"),
    ("settings", "Settings"),
    ("about", "About"),
)

VIEW_CLASSES: dict[str, type[BaseView]] = {
    "products": ProductsView,
    "categories": CategoriesView,
    "suppliers": SuppliersView,
}


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
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._current: str | None = None
        self._configure_window()
        self.theme.style_tables()
        self._build_layout()
        services.settings.subscribe(self._on_setting_changed)
        self.update_status_info()
        self.refresh_badge()
        self.show("dashboard")

    # -- construction -----------------------------------------------------------------
    def _configure_window(self) -> None:
        """Title, size and close handler from config."""
        cfg = self.config_data
        self.title(f"{cfg.get('app.name')} · v{cfg.get('app.version')}")
        # Never open larger than the screen (minus room for the taskbar).
        max_w = self.winfo_screenwidth() - cfg.get("ui.screen_margin")
        max_h = self.winfo_screenheight() - cfg.get("ui.screen_margin")
        width, height = min(cfg.get("ui.window_width"), max_w), min(cfg.get("ui.window_height"), max_h)
        x, y = (self.winfo_screenwidth() - width) // 2, max((max_h - height) // 2, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(min(cfg.get("ui.min_width"), max_w), min(cfg.get("ui.min_height"), max_h))
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self) -> None:
        """Sidebar, content area and status bar."""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=24, pady=(20, 12))
        self.status = StatusBar(self, self.theme, self.config_data.get("ui.toast_ms"))
        self.status.grid(row=1, column=0, columnspan=2, sticky="ew")

    def _build_sidebar(self) -> None:
        """Logo block and one navigation button per screen."""
        sidebar = ctk.CTkFrame(self, width=self.config_data.get("ui.sidebar_width"),
                               corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)
        ctk.CTkLabel(sidebar, text=self.config_data.get("app.short_name"),
                     font=self.theme.font(12, "bold")).pack(pady=(24, 0))
        ctk.CTkLabel(sidebar, text="Inventory · TQM Q11", font=self.theme.font(-2),
                     text_color=self.theme.color("muted")).pack(pady=(0, 20))
        for key, label in NAVIGATION:
            self._buttons[key] = self._nav_button(sidebar, key, label)
        self._badge = ctk.CTkLabel(self._buttons["products"], text="", width=26, height=20,
                                   corner_radius=10, fg_color=self.theme.color("danger"),
                                   text_color=self.theme.color("badge_fg"),
                                   font=self.theme.font(-2, "bold"))

    def _nav_button(self, sidebar: Any, key: str, label: str) -> ctk.CTkButton:
        """One flat sidebar button."""
        button = ctk.CTkButton(sidebar, text=label, anchor="w", height=36, corner_radius=8,
                               fg_color="transparent", text_color=("gray15", "gray85"),
                               hover_color=("gray80", "gray25"), font=self.theme.font(1),
                               command=lambda: self.show(key))
        button.pack(fill="x", padx=12, pady=2)
        return button

    # -- navigation -------------------------------------------------------------------
    def show(self, key: str) -> None:
        """Display the screen registered under ``key`` (created on first use)."""
        if self._current in self._views:
            self._views[self._current].pack_forget()
        view = self._views.get(key) or self._create_view(key)
        view.pack(fill="both", expand=True)
        self._current = key
        self._highlight(key)
        view.on_show()

    def _create_view(self, key: str) -> BaseView:
        """Instantiate and cache a screen."""
        view_class = VIEW_CLASSES.get(key, PlaceholderView)
        self._views[key] = view_class(self.content, self)
        return self._views[key]

    def _highlight(self, key: str) -> None:
        """Mark the active sidebar button."""
        for name, button in self._buttons.items():
            active = name == key
            button.configure(fg_color=self.theme.color("accent") if active else "transparent",
                             text_color=("white", "white") if active else ("gray15", "gray85"))

    # -- shared state -----------------------------------------------------------------
    def refresh_badge(self) -> None:
        """Update the low-stock count badge on the Products button."""
        count = self.services.products.low_stock_count()
        if count:
            self._badge.configure(text=str(count))
            self._badge.place(relx=1.0, rely=0.5, x=-10, anchor="e")
        else:
            self._badge.place_forget()

    def update_status_info(self) -> None:
        """Show operator, role, database and version in the status bar."""
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
        """Tk hook for exceptions escaping any callback: record and apologise."""
        self.services.activity.record_error("UI callback", val)
        show_error(self, "handling that action")

    def destroy(self) -> None:
        """Detach from settings notifications, then destroy the window."""
        self.services.settings.unsubscribe(self._on_setting_changed)
        super().destroy()

    def _on_close(self) -> None:
        """Close the database cleanly and exit."""
        self.destroy()
        self.services.db.close()
