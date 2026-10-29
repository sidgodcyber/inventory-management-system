"""System Settings screen: change runtime behaviour without editing code.

Every setting listed in ``core.settings_manager.SETTING_DEFINITIONS`` appears
here automatically, with its description and config.json default. Saving
validates all values first (all-or-nothing), writes one ``SETTINGS_CHANGE``
audit entry per changed value, and applies the change immediately: the
theme, page size, currency, date format, log level and status bar update
without a restart.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from core.settings_manager import SettingDefinition
from ui.components.confirm_dialog import ask_confirm
from ui.views.base_view import BaseView


class SettingsView(BaseView):
    """Edit, save and reset runtime settings."""

    title = "Settings"
    subtitle = ("Runtime settings are stored in the database and seeded from config/config.json. "
                "Changes apply immediately and are recorded in the Activity Log.")

    def build(self) -> None:
        """Action bar and one row per setting."""
        self._inputs: dict[str, Any] = {}
        self._build_actions()
        self.form = ctk.CTkScrollableFrame(self.body, corner_radius=10)
        self.form.pack(fill="both", expand=True)
        self.form.grid_columnconfigure(0, weight=1)
        for row, definition in enumerate(self.services.settings.definitions()):
            self._add_row(row, definition)

    def _build_actions(self) -> None:
        """Save / revert / reset buttons and the config file location."""
        bar = ctk.CTkFrame(self.body, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 10))
        source = self.services.config.source
        ctk.CTkLabel(bar, text=f"Defaults file: {source}", font=self.theme.font(-1),
                     text_color=self.theme.color("muted")).pack(side="left")
        for text, command, kind, width in (("Reset to defaults", self._reset, "danger", 140),
                                           ("Revert", self.refresh, "secondary", 90),
                                           ("Save changes", self._save, "primary", 130)):
            ctk.CTkButton(bar, text=text, width=width, command=command,
                          **self.theme.button_style(kind)).pack(side="right", padx=(8, 0))

    def _add_row(self, row: int, definition: SettingDefinition) -> None:
        """Add the label, description (with default) and input for one setting.

        Args:
            row: Grid row in the form.
            definition: Setting metadata (key, label, description).
        """
        text = ctk.CTkFrame(self.form, fg_color="transparent")
        text.grid(row=row, column=0, sticky="ew", padx=16, pady=8)
        ctk.CTkLabel(text, text=definition.label, font=self.theme.font(1, "bold"),
                     anchor="w").pack(fill="x")
        default = self.services.settings.defaults()[definition.key]
        ctk.CTkLabel(text, text=f"{definition.description}   ·   default: {default}",
                     font=self.theme.font(-1), text_color=self.theme.color("muted"),
                     anchor="w").pack(fill="x")
        widget = self._make_input(definition.key)
        widget.grid(row=row, column=1, sticky="e", padx=16, pady=8)
        self._inputs[definition.key] = widget

    def _make_input(self, key: str) -> Any:
        """Create the input widget that suits a setting.

        Args:
            key: Setting key.

        Returns:
            An option menu for fixed choices, a combo box when the choices are
            only suggestions (currency, date format), otherwise an entry.
        """
        settings = self.services.settings
        options = settings.options(key)
        if options and settings.is_free_choice(key):
            return ctk.CTkComboBox(self.form, values=options, width=240, font=self.theme.font())
        if options:
            return ctk.CTkOptionMenu(self.form, values=options, width=240,
                                     font=self.theme.font())
        return ctk.CTkEntry(self.form, width=240, font=self.theme.font())

    # -- data -------------------------------------------------------------------------
    def refresh(self) -> None:
        """Load the current values into the inputs.

        Also bound to the Revert button, which discards unsaved edits.
        """
        for key, value in self.services.settings.values().items():
            self._set_input(self._inputs[key], str(value))

    @staticmethod
    def _set_input(widget: Any, value: str) -> None:
        """Show a value in an entry, option menu or combo box.

        Args:
            widget: Input created by :meth:`_make_input`.
            value: Text to display.
        """
        if isinstance(widget, ctk.CTkEntry):
            widget.delete(0, "end")
            widget.insert(0, value)
        else:
            widget.set(value)

    def on_setting_changed(self, key: str, value: Any) -> None:
        """Keep the inputs in sync when a setting changes while this screen is open.

        Args:
            key: Changed setting.
            value: Its new value.
        """
        self._set_input(self._inputs[key], str(value))

    def _save(self) -> None:
        """Validate and save every value through the settings service.

        Saving is all-or-nothing; each real change is audited as SETTINGS_CHANGE
        and applied immediately by the listeners in the main window.
        """
        values = {key: widget.get() for key, widget in self._inputs.items()}
        changed = self.guarded("Settings > Save", lambda: self.services.settings.save(values))
        if changed is not None:
            self._report(changed, "Saved")

    def _reset(self) -> None:
        """Restore config.json defaults after confirmation."""
        if not ask_confirm(self, self.theme, "Reset settings",
                           "Restore every setting to the defaults in config/config.json? "
                           "Each change will be recorded in the Activity Log.", "Reset",
                           danger=True):
            return
        changed = self.guarded("Settings > Reset", self.services.settings.reset_to_defaults)
        if changed is not None:
            self.refresh()
            self._report(changed, "Reset")

    def _report(self, changed: dict[str, tuple[Any, Any]], verb: str) -> None:
        """Toast summarising what changed.

        Args:
            changed: ``{key: (old, new)}`` returned by the service.
            verb: "Saved" or "Reset".
        """
        if not changed:
            self.notify("No changes to save.", "info")
            return
        summary = ", ".join(f"{key}: {old} → {new}" for key, (old, new) in changed.items())
        self.notify(f"{verb} {len(changed)} setting(s): {summary}", "success")
