"""User model: an account that can sign in, with one role.

The password hash is deliberately left out of :meth:`User.audit_values`, so it
can never reach the activity log.

Layer: models
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from models.common import row_to_kwargs


@dataclass
class User:
    """A user account.

    Attributes:
        id: Primary key (``None`` until saved).
        username: Unique sign-in name (case-insensitive).
        full_name: Display name.
        role: One of ``core.constants.ROLES``.
        password_hash: PBKDF2 hash (see ``utils.passwords``).
        must_change_password: Force a new password at next sign-in.
        is_active: ``False`` once deactivated (cannot sign in).
        last_login_at: Time of the last successful sign-in.
        created_at: Creation timestamp.
        updated_at: Last-update timestamp.
    """

    id: int | None = None
    username: str = ""
    full_name: str = ""
    role: str = ""
    password_hash: str = ""
    must_change_password: bool = False
    is_active: bool = True
    last_login_at: str | None = None
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> User:
        """Build a user from a database row (SQLite stores booleans as 0/1)."""
        user = cls(**row_to_kwargs(cls, row))
        user.must_change_password = bool(user.must_change_password)
        user.is_active = bool(user.is_active)
        return user

    def audit_values(self) -> dict[str, Any]:
        """Fields safe to record in the audit trail (never the password hash).

        Returns:
            Username, full name, role and active flag.
        """
        return {"username": self.username, "full_name": self.full_name, "role": self.role,
                "is_active": self.is_active}

    def to_dict(self) -> dict[str, Any]:
        """Return the fields as a plain dictionary (without the password hash)."""
        values = asdict(self)
        values.pop("password_hash")
        return values
