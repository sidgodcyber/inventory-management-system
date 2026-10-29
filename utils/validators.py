"""Poka-Yoke input validation: catch bad data before it reaches the database.

:class:`Validator` turns raw form input (usually strings) into clean typed
values or raises :class:`~core.exceptions.ValidationError` with a message
written for the operator. All limits and patterns (text lengths, SKU, phone and
email formats) come from the ``validation`` section of ``config.json``; the
generic number/date/choice parsing lives in :mod:`utils.parsing`.

Layer: utils (stateless helpers, used by services)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date
from typing import Any

from config.config_loader import AppConfig
from core.exceptions import ValidationError
from utils.date_helpers import is_valid_strftime, parse_date
from utils.parsing import is_blank, parse_choice, parse_decimal, parse_int

__all__ = ["Validator", "is_blank", "is_valid_strftime"]


class Validator:
    """Config-driven field validators.

    Args:
        config: Source of lengths and regex patterns.
    """

    def __init__(self, config: AppConfig) -> None:
        self.text_max = config.get("validation.text_max_length")
        self.notes_max = config.get("validation.notes_max_length")
        self._sku = re.compile(config.get("validation.sku_pattern"))
        self._phone = re.compile(config.get("validation.phone_pattern"))
        self._email = re.compile(config.get("validation.email_pattern"))

    def text(self, value: Any, label: str, required: bool = True,
             max_length: int | None = None) -> str:
        """Trimmed text with a required check and a maximum length.

        Args:
            value: Raw input.
            label: Field name used in error messages.
            required: Refuse blank input.
            max_length: Override for the configured ``text_max_length``.

        Returns:
            The trimmed text.

        Raises:
            ValidationError: If missing or too long.
        """
        text = "" if value is None else str(value).strip()
        limit = max_length or self.text_max
        if required and not text:
            raise ValidationError(f"{label} is required.", label)
        if len(text) > limit:
            raise ValidationError(f"{label} must be at most {limit} characters.", label)
        return text

    def notes(self, value: Any, label: str = "Notes") -> str:
        """Optional long text limited to ``notes_max_length``.

        Args:
            value: Raw input.
            label: Field name used in error messages.

        Returns:
            The trimmed text (possibly empty).
        """
        return self.text(value, label, required=False, max_length=self.notes_max)

    def sku(self, value: Any) -> str:
        """Upper-cased SKU matching ``validation.sku_pattern``.

        Args:
            value: Raw input.

        Returns:
            The SKU in upper case.

        Raises:
            ValidationError: If blank or not matching the pattern.
        """
        sku = self.text(value, "SKU").upper()
        if not self._sku.fullmatch(sku):
            raise ValidationError(
                "SKU must be 2-20 characters: letters, digits and dashes "
                "(e.g. STA-PEN-001).", "SKU")
        return sku

    def email(self, value: Any, required: bool = False) -> str:
        """Email address in a valid format.

        Args:
            value: Raw input.
            required: Refuse blank input.

        Returns:
            The trimmed address (possibly empty when optional).

        Raises:
            ValidationError: If the format is wrong.
        """
        email = self.text(value, "Email", required=required)
        if email and not self._email.fullmatch(email):
            raise ValidationError("Email must look like name@example.com.", "Email")
        return email

    def phone(self, value: Any, required: bool = False) -> str:
        """Phone number: digits, spaces, dashes and a leading +.

        Args:
            value: Raw input.
            required: Refuse blank input.

        Returns:
            The trimmed number (possibly empty when optional).

        Raises:
            ValidationError: If the format is wrong.
        """
        phone = self.text(value, "Phone", required=required)
        if phone and not self._phone.fullmatch(phone):
            raise ValidationError(
                "Phone must contain 7-15 digits (spaces, dashes and a leading + allowed).",
                "Phone")
        return phone

    # Generic parsers exposed through the validator for a single entry point.
    @staticmethod
    def integer(value: Any, label: str, minimum: int | None = None,
                maximum: int | None = None) -> int:
        """Whole number within optional bounds (see :func:`utils.parsing.parse_int`)."""
        return parse_int(value, label, minimum, maximum)

    @staticmethod
    def decimal(value: Any, label: str, minimum: float = 0.0) -> float:
        """Non-negative decimal (see :func:`utils.parsing.parse_decimal`)."""
        return parse_decimal(value, label, minimum)

    @staticmethod
    def choice(value: Any, label: str, allowed: Iterable[str]) -> str:
        """One of ``allowed`` (see :func:`utils.parsing.parse_choice`)."""
        return parse_choice(value, label, allowed)

    @staticmethod
    def date(value: Any, label: str, fmt: str) -> date | None:
        """Optional date in the display format (see :func:`utils.date_helpers.parse_date`)."""
        return parse_date(value, label, fmt)
