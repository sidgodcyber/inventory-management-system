"""Tests for :mod:`repositories.user_repository`.

Layer: tests
Author: Siddhi Baluja
"""

from __future__ import annotations

import pytest

from core.constants import ROLE_ADMIN, ROLE_STAFF
from core.database import Database
from core.exceptions import DatabaseError
from models.common import ListQuery
from models.user import User
from repositories.user_repository import UserRepository


@pytest.fixture()
def repo(db: Database) -> UserRepository:
    """Repository bound to the temporary database."""
    return UserRepository(db)


def _user(username: str = "asha", role: str = ROLE_STAFF) -> User:
    """Unsaved user with a dummy hash."""
    return User(username=username, full_name=username.title(), role=role, password_hash="x$y")


def test_create_and_lookup_case_insensitive(repo: UserRepository) -> None:
    """Usernames are unique regardless of case."""
    new_id = repo.create(_user())
    assert repo.get_by_username("ASHA").id == new_id
    with pytest.raises(DatabaseError, match="UNIQUE"):
        repo.create(_user("Asha"))


def test_role_is_constrained(repo: UserRepository) -> None:
    """Only the defined roles are accepted by the schema."""
    with pytest.raises(DatabaseError, match="CHECK"):
        repo.create(_user(role="Owner"))


def test_profile_password_active_and_login(repo: UserRepository) -> None:
    """Updates persist and booleans come back typed."""
    new_id = repo.create(_user())
    repo.update_profile(new_id, "Asha Verma", ROLE_ADMIN)
    repo.set_password(new_id, "new$hash", must_change=True)
    repo.set_active(new_id, False)
    repo.record_login(new_id)
    user = repo.get(new_id)
    assert (user.full_name, user.role, user.password_hash) == ("Asha Verma", ROLE_ADMIN, "new$hash")
    assert user.must_change_password is True and user.is_active is False
    assert user.last_login_at


def test_find_and_admin_count(repo: UserRepository) -> None:
    """Search works and only active admins are counted."""
    repo.create(_user("admin", ROLE_ADMIN))
    second = repo.create(_user("boss", ROLE_ADMIN))
    repo.create(_user("asha"))
    repo.set_active(second, False)
    assert repo.count_active_admins() == 1 and repo.count() == 3
    assert repo.find(ListQuery(search="Store Staff")).total == 1


def test_audit_values_never_include_hash() -> None:
    """The password hash cannot leak into audit payloads or dict exports."""
    user = _user()
    assert "password_hash" not in user.audit_values()
    assert "password_hash" not in user.to_dict()
