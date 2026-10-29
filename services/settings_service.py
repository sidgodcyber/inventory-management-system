"""System Settings: validate, save, reset and apply runtime settings.

Every saved change writes a ``SETTINGS_CHANGE`` activity entry with old and new
values, inside the same transaction as the change itself. The log level is
applied immediately through :func:`core.logger.set_log_level`. Other consumers
(theme, page size, currency, operator name in the status bar) subscribe via
:meth:`SettingsService.subscribe` and react without a restart.

Layer: services
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from config.config_loader import AppConfig
from core.constants import APPEARANCE_MODES, ACTION_SETTINGS_CHANGE, ENTITY_SETTING, LOG_LEVELS
from core.database import Database
from core.exceptions import ValidationError
from core.logger import log_activity, set_log_level
from core.settings_manager import SettingDefinition, SettingListener, SettingsManager
from utils.validators import Validator, is_valid_strftime

Change = tuple[Any, Any]


class SettingsService:
    """Business rules for the Settings screen.

    Args:
        manager: Typed settings store.
        validator: Field validator.
        db: Database, used only to open atomic transactions.
        config: Source of defaults, choices and validation bounds.
    """

    def __init__(self, manager: SettingsManager, validator: Validator, db: Database,
                 config: AppConfig) -> None:
        self._manager = manager
        self._validate = validator
        self._db = db
        self._config = config
        self._rules: dict[str, Callable[[Any, str], Any]] = self._build_rules()
        manager.subscribe(self._apply_side_effects)

    # -- read ---------------------------------------------------------------------
    def definitions(self) -> tuple[SettingDefinition, ...]:
        """Setting definitions in display order."""
        return self._manager.definitions

    def get(self, key: str) -> Any:
        """Current typed value of one setting."""
        return self._manager.get(key)

    def values(self) -> dict[str, Any]:
        """All current values."""
        return self._manager.get_all()

    def defaults(self) -> dict[str, Any]:
        """config.json defaults for every setting."""
        return {d.key: self._manager.default(d.key) for d in self._manager.definitions}

    def options(self, key: str) -> list[str] | None:
        """Choices offered for a setting, or ``None`` for free input."""
        choices = {
            "appearance_mode": list(APPEARANCE_MODES),
            "log_level": list(LOG_LEVELS),
            "operator_role": self._config.get("operator.roles"),
            "currency_symbol": self._config.get("inventory.currency_options"),
            "date_format": self._config.get("display.date_format_options"),
        }
        return choices.get(key)

    def is_free_choice(self, key: str) -> bool:
        """True when options are suggestions and any valid value may be typed."""
        return key in ("currency_symbol", "date_format")

    # -- write --------------------------------------------------------------------
    def save(self, changes: Mapping[str, Any]) -> dict[str, Change]:
        """Validate every value, then persist and audit the ones that changed.

        Args:
            changes: ``{setting key: raw value}`` from the form.

        Returns:
            ``{key: (old, new)}`` for settings that actually changed.

        Raises:
            ValidationError: If any value is invalid (nothing is saved).
        """
        clean = {key: self._clean(key, value) for key, value in changes.items()}
        applied: dict[str, Change] = {}
        try:
            with self._db.transaction():
                for key, value in clean.items():
                    old, new = self._manager.set(key, value)
                    if old != new:
                        applied[key] = (old, new)
                        log_activity(ACTION_SETTINGS_CHANGE, ENTITY_SETTING, key,
                                     {"old": old, "new": new})
        except Exception:
            self._manager.reload()  # cache may hold values that were rolled back
            raise
        return applied

    def reset_to_defaults(self) -> dict[str, Change]:
        """Restore every setting to its config.json default (audited)."""
        return self.save(self.defaults())

    def subscribe(self, listener: SettingListener) -> None:
        """Run ``listener(key, value)`` after each change (used by the UI)."""
        self._manager.subscribe(listener)

    def apply_startup(self) -> None:
        """Apply settings that affect infrastructure when the app starts."""
        set_log_level(self._manager.get("log_level"))

    # -- validation ---------------------------------------------------------------
    def _clean(self, key: str, value: Any) -> Any:
        """Validate one value with the rule registered for ``key``."""
        definition = self._manager.definition(key)
        return self._rules[key](value, definition.label)

    def _build_rules(self) -> dict[str, Callable[[Any, str], Any]]:
        """Map each setting key to its validation rule."""
        v, cfg = self._validate, self._config
        return {
            "appearance_mode": lambda x, label: v.choice(x, label, APPEARANCE_MODES),
            "currency_symbol": lambda x, label: v.text(
                x, label, max_length=cfg.get("validation.currency_max_length")),
            "default_reorder_level": lambda x, label: v.integer(
                x, label, minimum=0, maximum=cfg.get("validation.reorder_level_max")),
            "page_size": lambda x, label: v.integer(
                x, label, cfg.get("validation.page_size_min"),
                cfg.get("validation.page_size_max")),
            "date_format": self._date_format,
            "log_level": lambda x, label: v.choice(str(x).upper(), label, LOG_LEVELS),
            "log_retention_days": lambda x, label: v.integer(
                x, label, cfg.get("validation.retention_days_min"),
                cfg.get("validation.retention_days_max")),
            "operator_name": lambda x, label: v.text(x, label),
            "operator_role": lambda x, label: v.choice(x, label, cfg.get("operator.roles")),
        }

    def _date_format(self, value: Any, label: str) -> str:
        """A strftime pattern that round-trips a date (e.g. ``%d-%m-%Y``)."""
        fmt = self._validate.text(value, label)
        if not is_valid_strftime(fmt):
            raise ValidationError(
                f"{label} must contain day, month and year codes, e.g. %d-%m-%Y.", label)
        return fmt

    @staticmethod
    def _apply_side_effects(key: str, value: Any) -> None:
        """Apply settings that the service layer owns (log level)."""
        if key == "log_level":
            set_log_level(value)
