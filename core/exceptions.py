"""Custom exception hierarchy used across the application.

Every error the user may legitimately cause derives from :class:`AppError`, so
the UI can show its ``message`` in a friendly dialog. Anything that is *not* an
``AppError`` is treated as a defect: it is logged with action ``ERROR`` and the
user sees a generic apology instead of a traceback.

Layer: core (leaf module, usable by every layer)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for expected, user-facing errors.

    Args:
        message: Human-readable explanation suitable for a dialog box.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(AppError):
    """Input failed a validation (Poka-Yoke) rule.

    Args:
        message: What is wrong and how to fix it.
        field: Optional name of the offending form field.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class NotFoundError(AppError):
    """A requested record does not exist (or was soft-deleted)."""


class StockError(AppError):
    """A stock movement would break an inventory rule, e.g. negative stock."""


class DatabaseError(AppError):
    """The database rejected an operation (constraint, lock or I/O failure)."""
