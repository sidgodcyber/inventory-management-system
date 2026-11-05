"""Change-password dialog for the signed-in user (also forced at first sign-in).

Layer: ui/views
Author: Siddhi Baluja
"""

from __future__ import annotations

from typing import Any

from core.exceptions import AppError
from services.container import AppServices
from ui.components.form_dialog import FormDialog, FormField
from ui.theme import Theme


def ask_new_password(master: Any, theme: Theme, services: AppServices, forced: bool) -> bool:
    """Show the dialog and wait until it closes.

    Args:
        master: Main window.
        theme: Shared theme.
        services: Service container (the auth service changes the password).
        forced: First sign-in or after a reset, when a new password is required.

    Returns:
        ``True`` when the password was changed.
    """
    changed: list[bool] = []

    def submit(values: dict[str, str]) -> str | None:
        """Change the password; return an inline error message on failure."""
        try:
            services.auth.change_own_password(values["current"], values["new"],
                                              values["confirm"])
        except AppError as exc:
            return exc.message
        changed.append(True)
        return None

    minimum = services.config.get("auth.min_password_length")
    fields = [
        FormField("current", "Current (temporary) password" if forced else "Current password",
                  required=True, secret=True),
        FormField("new", "New password", required=True, secret=True,
                  hint=f"At least {minimum} characters"),
        FormField("confirm", "Confirm new password", required=True, secret=True),
    ]
    title = "Set a new password to continue" if forced else "Change password"
    dialog = FormDialog(master, theme, title, fields, on_submit=submit, submit_text="Change")
    master.wait_window(dialog)
    return bool(changed)
