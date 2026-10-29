"""Generic parsers that turn raw form text into typed values or raise ValidationError.

These are configuration-free building blocks; :class:`utils.validators.Validator`
adds the config-driven rules (lengths, SKU/email/phone patterns) on top. Date
parsing lives with the other date helpers in :mod:`utils.date_helpers`.

Layer: utils (stateless helpers)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from core.exceptions import ValidationError


def is_blank(value: Any) -> bool:
    """Check for a missing value.

    Args:
        value: Anything typed into a form.

    Returns:
        ``True`` for ``None`` or a string containing only whitespace.
    """
    return value is None or (isinstance(value, str) and not value.strip())


def parse_int(value: Any, label: str, minimum: int | None = None,
              maximum: int | None = None) -> int:
    """Parse a whole number within optional bounds.

    Args:
        value: Raw input.
        label: Field name used in error messages.
        minimum: Smallest allowed value.
        maximum: Largest allowed value.

    Returns:
        The parsed integer.

    Raises:
        ValidationError: If blank, not a whole number or out of range.
    """
    if is_blank(value):
        raise ValidationError(f"{label} is required.", label)
    try:
        number = int(str(value).strip())
    except ValueError as exc:
        raise ValidationError(f"{label} must be a whole number.", label) from exc
    if minimum is not None and number < minimum:
        raise ValidationError(f"{label} must be at least {minimum}.", label)
    if maximum is not None and number > maximum:
        raise ValidationError(f"{label} must be at most {maximum}.", label)
    return number


def parse_decimal(value: Any, label: str, minimum: float = 0.0) -> float:
    """Parse a decimal number rounded to 2 places.

    Args:
        value: Raw input.
        label: Field name used in error messages.
        minimum: Smallest allowed value (0 by default: no negative money).

    Returns:
        The parsed, rounded number.

    Raises:
        ValidationError: If blank, not numeric, NaN or below ``minimum``.
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


def parse_choice(value: Any, label: str, allowed: Iterable[str]) -> str:
    """Accept only one of a fixed set of values.

    Args:
        value: Raw input.
        label: Field name used in error messages.
        allowed: Permitted values.

    Returns:
        The trimmed value.

    Raises:
        ValidationError: If the value is not in ``allowed``.
    """
    options = list(allowed)
    text = "" if value is None else str(value).strip()
    if text not in options:
        raise ValidationError(f"{label} must be one of: {', '.join(options)}.", label)
    return text
