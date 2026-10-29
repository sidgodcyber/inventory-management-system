"""Display formatting for money, numbers, dates, ratios and durations.

Every function receives its formatting preference (currency symbol, date
format) as an argument, taken by the caller from the runtime settings, so
none of them hard-codes a locale.

Layer: utils (stateless helpers)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from datetime import datetime

from core.constants import DB_TIMESTAMP_FORMAT


def format_currency(amount: float | None, symbol: str) -> str:
    """Format money with thousands separators, e.g. ``₹1,234.50``.

    Args:
        amount: Value to format (``None`` is treated as 0).
        symbol: Currency symbol from settings.

    Returns:
        The formatted string; negatives are shown as ``-₹12.00``.
    """
    value = float(amount or 0)
    sign = "-" if value < 0 else ""
    return f"{sign}{symbol}{abs(value):,.2f}"


def format_number(value: float | None, decimals: int = 0) -> str:
    """Format a number with thousands separators."""
    return f"{float(value or 0):,.{decimals}f}"


def _parse_timestamp(timestamp: str) -> datetime | None:
    """Parse a DB timestamp (or bare date); ``None`` when blank or invalid."""
    text = (timestamp or "").strip()
    for fmt in (DB_TIMESTAMP_FORMAT, "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def format_date(timestamp: str, date_format: str) -> str:
    """Render the date part of a DB timestamp in the user's date format.

    Returns:
        The formatted date, or the original text if it cannot be parsed.
    """
    parsed = _parse_timestamp(timestamp)
    return parsed.strftime(date_format) if parsed else (timestamp or "")


def format_datetime(timestamp: str, date_format: str) -> str:
    """Render a DB timestamp as ``<date in user format> HH:MM``."""
    parsed = _parse_timestamp(timestamp)
    return f"{parsed.strftime(date_format)} {parsed:%H:%M}" if parsed else (timestamp or "")


def format_ratio(value: float | None) -> str:
    """Format a turnover ratio, e.g. ``2.35x``."""
    return f"{float(value or 0):.2f}x"


def format_days(days: float | None) -> str:
    """Format days of stock remaining; ``None`` means no recent usage."""
    if days is None:
        return "No usage"
    return f"{days:,.1f} days"


def truncate(text: str, length: int) -> str:
    """Shorten ``text`` to ``length`` characters, adding an ellipsis."""
    return text if len(text) <= length else f"{text[: max(length - 1, 0)]}…"
