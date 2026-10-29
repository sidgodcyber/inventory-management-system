"""Base class for every screen: header, settings-aware formatting, safe calls.

:meth:`BaseView.guarded` and :meth:`BaseView.form_call` are the *only* ways
views invoke services. Both catch exceptions, ask the activity service to
record them (action ``ERROR``), and show a friendly message, so a raw
traceback can never reach the operator.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

import customtkinter as ctk

from core.exceptions import AppError
from ui.components.messages import show_error, show_warning
from utils.formatters import format_currency, format_date, format_datetime

if TYPE_CHECKING:
    from ui.app import App

T = TypeVar("T")


class BaseView(ctk.CTkFrame):
    """Common behaviour for content screens.

    Args:
        master: Content area of the main window.
        app: The main window (gives access to services, theme, status bar).
    """

    #: Page title and subtitle shown in the header (override in subclasses).
    title: str = ""
    subtitle: str = ""

    def __init__(self, master: Any, app: App) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.services = app.services
        self.theme = app.theme
        self._build_header()
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True)
        self.build()

    # -- hooks for subclasses ----------------------------------------------------------
    def build(self) -> None:
        """Create the screen's widgets (override)."""

    def refresh(self) -> None:
        """Reload data from services (override)."""

    def on_show(self) -> None:
        """Called every time the screen becomes visible."""
        self.refresh()

    def on_setting_changed(self, key: str, value: Any) -> None:
        """React to a runtime setting change while this screen is visible."""
        if key in ("page_size", "currency_symbol", "date_format"):
            self.refresh()

    # -- layout helpers -----------------------------------------------------------------
    def _build_header(self) -> None:
        """Title and subtitle at the top of the screen."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(header, text=self.title, font=self.theme.heading_font(),
                     anchor="w").pack(fill="x")
        if self.subtitle:
            ctk.CTkLabel(header, text=self.subtitle, font=self.theme.font(-1),
                         text_color=self.theme.color("muted"), anchor="w").pack(fill="x")

    # -- settings-aware formatting ------------------------------------------------------
    def setting(self, key: str) -> Any:
        """Current value of a runtime setting."""
        return self.services.settings.get(key)

    def money(self, amount: float | None) -> str:
        """Format money with the configured currency symbol."""
        return format_currency(amount, self.setting("currency_symbol"))

    def date_text(self, timestamp: str) -> str:
        """Format a DB timestamp's date with the configured date format."""
        return format_date(timestamp, self.setting("date_format"))

    def datetime_text(self, timestamp: str) -> str:
        """Format a DB timestamp with date (configured format) and time."""
        return format_datetime(timestamp, self.setting("date_format"))

    def notify(self, text: str, kind: str = "info") -> None:
        """Show a toast in the status bar."""
        self.app.status.show(text, kind)

    # -- safe service calls -------------------------------------------------------------
    def guarded(self, context: str, action: Callable[[], T]) -> T | None:
        """Run ``action``; on failure record the error and show a message box.

        Args:
            context: Human-readable place, e.g. ``"Products > Delete"``.
            action: Zero-argument callable that calls a service.

        Returns:
            The action's result, or ``None`` if it failed.
        """
        try:
            return action()
        except AppError as exc:
            self.services.activity.record_error(context, exc)
            show_warning(self, context, exc.message)
        except Exception as exc:  # noqa: BLE001 - last line of defence for the UI
            self.services.activity.record_error(context, exc)
            show_error(self, context)
        return None

    def form_call(self, context: str, action: Callable[[], Any],
                  on_success: Callable[[Any], None] | None = None) -> str | None:
        """Run ``action`` for a form dialog and return an inline error message.

        Args:
            context: Human-readable place, e.g. ``"Suppliers > Add"``.
            action: Zero-argument callable that calls a service.
            on_success: Called with the action's result when it succeeds.

        Returns:
            ``None`` on success (the dialog closes) or the message to display.
        """
        try:
            result = action()
        except AppError as exc:
            self.services.activity.record_error(context, exc)
            return exc.message
        except Exception as exc:  # noqa: BLE001 - last line of defence for the UI
            self.services.activity.record_error(context, exc)
            show_error(self, context)
            return "Unexpected error. See the Activity Log for details."
        if on_success is not None:
            on_success(result)
        return None
