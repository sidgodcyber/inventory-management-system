"""Data access for the ``users`` table.

Layer: repositories
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

from core.constants import ROLE_ADMIN
from models.common import ListQuery, Page
from models.user import User
from repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """CRUD and search for user accounts."""

    SORT_COLUMNS = {
        "username": "username",
        "full_name": "full_name",
        "role": "role",
        "is_active": "is_active",
        "last_login_at": "last_login_at",
    }
    DEFAULT_SORT = "username"

    def create(self, user: User) -> int:
        """Insert a user and return the new id.

        Args:
            user: Account with ``password_hash`` already set.

        Returns:
            The new user id.
        """
        now = self.now()
        cursor = self.db.execute(
            "INSERT INTO users (username, full_name, role, password_hash, must_change_password, "
            "is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (user.username, user.full_name, user.role, user.password_hash,
             int(user.must_change_password), now, now),
        )
        return int(cursor.lastrowid)

    def update_profile(self, user_id: int, full_name: str, role: str) -> None:
        """Change a user's display name and role."""
        self.db.execute("UPDATE users SET full_name = ?, role = ?, updated_at = ? WHERE id = ?",
                        (full_name, role, self.now(), user_id))

    def set_password(self, user_id: int, password_hash: str, must_change: bool) -> None:
        """Store a new password hash and the must-change flag."""
        self.db.execute(
            "UPDATE users SET password_hash = ?, must_change_password = ?, updated_at = ? "
            "WHERE id = ?", (password_hash, int(must_change), self.now(), user_id))

    def set_active(self, user_id: int, active: bool) -> None:
        """Deactivate (``False``) or reactivate (``True``) an account."""
        self.db.execute("UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?",
                        (int(active), self.now(), user_id))

    def record_login(self, user_id: int) -> None:
        """Remember the time of a successful sign-in."""
        self.db.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (self.now(), user_id))

    def get(self, user_id: int) -> User | None:
        """Return one user or ``None``."""
        row = self.db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        return User.from_row(row) if row else None

    def get_by_username(self, username: str) -> User | None:
        """Return the user with this username (case-insensitive) or ``None``."""
        row = self.db.query_one("SELECT * FROM users WHERE username = ?", (username.strip(),))
        return User.from_row(row) if row else None

    def find(self, query: ListQuery) -> Page[User]:
        """Search (username, full name, role), sort and paginate users.

        Args:
            query: Search, sort and page.

        Returns:
            One page of users.
        """
        clauses: list[str] = []
        params: list[Any] = []
        if query.search.strip():
            clauses.append("(username LIKE ? OR full_name LIKE ? OR role LIKE ?)")
            params += [self.like(query.search)] * 3
        where = self.where(clauses)
        return self.paginate(f"SELECT * FROM users{where}",
                             f"SELECT COUNT(*) FROM users{where}", params, query, User.from_row)

    def count(self) -> int:
        """Total number of accounts (active or not)."""
        return int(self.db.query_value("SELECT COUNT(*) FROM users", default=0))

    def count_active_admins(self) -> int:
        """Number of active Admin accounts (at least one must always remain)."""
        return int(self.db.query_value(
            "SELECT COUNT(*) FROM users WHERE role = ? AND is_active = 1", (ROLE_ADMIN,), 0))
