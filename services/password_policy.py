"""Password policy: validate new passwords and turn them into stored hashes.

Shared by the sign-in service (changing your own password, bootstrap admin)
and the user service (new accounts, resets). The minimum length and the PBKDF2
work factor come from the ``auth`` section of ``config.json``.

Layer: services
Author: Siddhi Baluja
"""

from __future__ import annotations

from config.config_loader import AppConfig
from core.exceptions import ValidationError
from utils.passwords import hash_password
from utils.validators import Validator


class PasswordPolicy:
    """Config-driven password rules.

    Args:
        validator: Field validator (required check and maximum length).
        config: Source of ``auth.min_password_length`` and ``auth.pbkdf2_iterations``.
    """

    def __init__(self, validator: Validator, config: AppConfig) -> None:
        self._validate = validator
        self._config = config

    def hash_new(self, password: str, label: str = "Password") -> str:
        """Check the policy and hash a new password.

        Args:
            password: Proposed plain-text password.
            label: Field name used in error messages.

        Returns:
            The encoded PBKDF2 hash.

        Raises:
            ValidationError: If the password is blank or shorter than the minimum.
        """
        minimum = self._config.get("auth.min_password_length")
        text = self._validate.text(password, label)
        if len(text) < minimum:
            raise ValidationError(f"{label} must be at least {minimum} characters.", label)
        return self.hash_trusted(text)

    def hash_trusted(self, password: str) -> str:
        """Hash a password from configuration without the policy check.

        Args:
            password: Plain-text password (e.g. the initial admin password).

        Returns:
            The encoded PBKDF2 hash.
        """
        return hash_password(password, self._config.get("auth.pbkdf2_iterations"))

    @staticmethod
    def check_change(current: str, new: str, confirm: str) -> None:
        """A new password must match its confirmation and differ from the old one.

        Args:
            current: Current password.
            new: Proposed password.
            confirm: Proposed password typed again.

        Raises:
            ValidationError: If either rule is broken.
        """
        if new != confirm:
            raise ValidationError("The new passwords do not match.", "Confirm password")
        if new == current:
            raise ValidationError("Choose a password different from the current one.",
                                  "New password")
