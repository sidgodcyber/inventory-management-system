"""Date and period helpers built on the database timestamp format.

Layer: utils (stateless helpers)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from core.constants import DB_TIMESTAMP_FORMAT
from core.exceptions import ValidationError
from utils.parsing import is_blank


def to_timestamp(moment: datetime) -> str:
    """Format a datetime as a DB timestamp string."""
    return moment.strftime(DB_TIMESTAMP_FORMAT)


def now_timestamp() -> str:
    """Current local time as a DB timestamp string."""
    return to_timestamp(datetime.now())


def days_ago(days: int, today: date | None = None) -> date:
    """The calendar date ``days`` days before ``today`` (default: today)."""
    return (today or date.today()) - timedelta(days=days)


def start_of_day(day: date) -> str:
    """DB timestamp for 00:00:00 on ``day``."""
    return to_timestamp(datetime.combine(day, datetime.min.time()))


def end_of_day(day: date) -> str:
    """DB timestamp for 23:59:59 on ``day``."""
    return to_timestamp(datetime.combine(day, datetime.max.time().replace(microsecond=0)))


def period_bounds(start: date, end: date) -> tuple[str, str]:
    """Inclusive DB-timestamp bounds covering whole days ``start``..``end``."""
    return start_of_day(start), end_of_day(end)


def days_between(start: date, end: date) -> int:
    """Inclusive number of days in ``start``..``end`` (minimum 1)."""
    return max((end - start).days + 1, 1)


def date_range(start: date, end: date) -> list[date]:
    """Every date from ``start`` to ``end`` inclusive."""
    return [start + timedelta(days=offset) for offset in range(days_between(start, end))]


def is_valid_strftime(fmt: str) -> bool:
    """Check that a date format contains day, month and year.

    Args:
        fmt: A ``strftime`` pattern such as ``%d-%m-%Y``.

    Returns:
        ``True`` when formatting a date and parsing it back gives the same day.
    """
    if not fmt or "%" not in fmt:
        return False
    sample = date(2026, 12, 31)
    try:
        return datetime.strptime(sample.strftime(fmt), fmt).date() == sample
    except ValueError:
        return False


def parse_date(value: Any, label: str, fmt: str) -> date | None:
    """Parse an optional date typed in the configured display format.

    Args:
        value: Raw input; blank means "no date".
        label: Field name used in error messages.
        fmt: ``strftime`` pattern from the ``date_format`` setting.

    Returns:
        The date, or ``None`` when blank.

    Raises:
        ValidationError: If the text does not match ``fmt``.
    """
    if is_blank(value):
        return None
    try:
        return datetime.strptime(str(value).strip(), fmt).date()
    except ValueError as exc:
        example = date.today().strftime(fmt)
        raise ValidationError(f"{label} must be a date like {example}.", label) from exc
