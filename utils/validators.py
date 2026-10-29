"""Poka-Yoke input validation: catch bad data before it reaches the database.

:class:`Validator` turns raw form input (usually strings) into clean typed
values or raises :class:`~core.exceptions.ValidationError` with a message
written for the operator. All limits and patterns (text lengths, SKU, phone and
email formats) come from the ``validation`` section of ``config.json``.

Layer: utils (stateless helpers, used by services)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from config.config_loader import AppConfig
from core.exceptions import ValidationError


def is_blank(value: Any) -> bool:
    """True for ``None`` or a string containing only whitespace."""
    return value is None or (isinstance(value, str) and not value.strip())


def is_valid_strftime(fmt: str) -> bool:
    """True when ``fmt`` formats a date and parses it back to the same day."""
    if not fmt or "%" not in fmt:
        return False
    sample = date(2026, 12, 31)
    try:
        return datetime.strptime(sample.strftime(fmt), fmt).date() == sample
    except ValueError:
        return False


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
        """Optional long text limited to ``notes_max_length``."""
        return self.text(value, label, required=False, max_length=self.notes_max)

    def integer(self, value: Any, label: str, minimum: int | None = None,
                maximum: int | None = None) -> int:
        """Whole number within optional bounds.

        Raises:
            ValidationError: If not a whole number or out of range.
        """
        if is_blank(value):
            raise ValidationError(f"{label} is required.", label)
        try:
            number = int(str(value).strip())
        except ValueError as exc:
            raise ValidationError(f"{label} must be a whole number.", label) from exc
        _check_bounds(number, label, minimum, maximum)
        return number

    def decimal(self, value: Any, label: str, minimum: float = 0.0) -> float:
        """Non-negative (by default) decimal rounded to 2 places.

        Raises:
            ValidationError: If not numeric or below ``minimum``.
        """
        if is_blank(value):
            raise ValidationError(f"{label} is required.", label)
        try:
            number = float(str(value).strip())
        except ValueError as exc:
            raise ValidationError(f"{label} must be a number.", label) from exc
        if number != number or number < minimum:  # number != number catches NaN
            raise ValidationError(f"{label} must be at least {minimum:g}.", label)
        return round(number, 2)

    def sku(self, value: Any) -> str:
        """Upper-cased SKU matching ``validation.sku_pattern``."""
        sku = self.text(value, "SKU").upper()
        if not self._sku.fullmatch(sku):
            raise ValidationError(
                "SKU must be 2-20 characters: letters, digits and dashes "
                "(e.g. STA-PEN-001).", "SKU"
            )
        return sku

    def email(self, value: Any, required: bool = False) -> str:
        """Optional email address in a valid format."""
        email = self.text(value, "Email", required=required)
        if email and not self._email.fullmatch(email):
            raise ValidationError("Email must look like name@example.com.", "Email")
        return email

    def phone(self, value: Any, required: bool = False) -> str:
        """Optional phone number: digits, spaces, dashes and a leading +."""
        phone = self.text(value, "Phone", required=required)
        if phone and not self._phone.fullmatch(phone):
            raise ValidationError(
                "Phone must contain 7-15 digits (spaces, dashes and a leading + allowed).",
                "Phone",
            )
        return phone

    @staticmethod
    def choice(value: Any, label: str, allowed: Iterable[str]) -> str:
        """Value that must be one of ``allowed``."""
        options = list(allowed)
        text = "" if value is None else str(value).strip()
        if text not in options:
            raise ValidationError(f"{label} must be one of: {', '.join(options)}.", label)
        return text

    @staticmethod
    def date(value: Any, label: str, fmt: str) -> date | None:
        """Optional date typed in the configured display format."""
        if is_blank(value):
            return None
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError as exc:
            example = date.today().strftime(fmt)
            raise ValidationError(f"{label} must be a date like {example}.", label) from exc


def _check_bounds(number: int, label: str, minimum: int | None, maximum: int | None) -> None:
    """Raise when ``number`` falls outside the optional bounds."""
    if minimum is not None and number < minimum:
        raise ValidationError(f"{label} must be at least {minimum}.", label)
    if maximum is not None and number > maximum:
        raise ValidationError(f"{label} must be at most {maximum}.", label)
