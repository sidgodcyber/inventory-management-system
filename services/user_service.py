"""User account management (Admin only): create, edit role, reset password, (de)activate.

Safety rules: an Admin cannot deactivate their own account, and the last
active Admin can be neither deactivated nor demoted, so the system can never
be left without someone able to manage it. Password hashes never reach the
audit trail.

Layer: services
Author: Siddhi Baluja
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.constants import ACTION_CREATE, ACTION_UPDATE, ENTITY_USER, ROLE_ADMIN, ROLES
from core.database import Database
from core.exceptions import NotFoundError, ValidationError
from core.logger import diff_changes, log_activity
from models.common import ListQuery, Page
from models.user import User
from repositories.user_repository import UserRepository
from services.auth_service import AuthService
from services.permissions import MANAGE_USERS
from utils.validators import Validator


class UserService:
    """Administer user accounts.

    Args:
        repo: User repository.
        auth: Session, permission checks and password policy.
        validator: Field validator.
        db: Database, used only to open atomic transactions.
    """

    def __init__(self, repo: UserRepository, auth: AuthService, validator: Validator,
                 db: Database) -> None:
        self._repo = repo
        self._auth = auth
        self._validate = validator
        self._db = db

    def find(self, query: ListQuery) -> Page[User]:
        """One page of accounts.

        Args:
            query: Search, sort and page.

        Returns:
            The requested page.

        Raises:
            PermissionDeniedError: Unless the user may manage users.
        """
        self._auth.require(MANAGE_USERS)
        return self._repo.find(query)

    def get(self, user_id: int) -> User:
        """Load one account.

        Raises:
            PermissionDeniedError: Unless the user may manage users.
            NotFoundError: If it does not exist.
        """
        self._auth.require(MANAGE_USERS)
        user = self._repo.get(user_id)
        if user is None:
            raise NotFoundError(f"User #{user_id} no longer exists.")
        return user

    def create(self, data: Mapping[str, Any]) -> User:
        """Create an account; the user must change the initial password at first sign-in.

        Args:
            data: ``username``, ``full_name``, ``role`` and ``password``.

        Returns:
            The new account.

        Raises:
            PermissionDeniedError: Unless the user may manage users.
            ValidationError: For a blank, duplicate or malformed field.
        """
        self._auth.require(MANAGE_USERS)
        username = self._validate.text(data.get("username"), "Username")
        if self._repo.get_by_username(username):
            raise ValidationError(f"The username '{username}' is already taken.", "Username")
        user = User(username=username, full_name=self._validate.text(data.get("full_name"), "Name"),
                    role=self._validate.choice(data.get("role"), "Role", ROLES),
                    password_hash=self._auth.policy.hash_new(data.get("password", "")),
                    must_change_password=True)
        with self._db.transaction():
            user.id = self._repo.create(user)
            log_activity(ACTION_CREATE, ENTITY_USER, user.id, {"new": user.audit_values()})
        return self.get(user.id)

    def update(self, user_id: int, data: Mapping[str, Any]) -> User:
        """Change an account's name and role.

        Args:
            user_id: Account to change.
            data: ``full_name`` and ``role``.

        Returns:
            The updated account.

        Raises:
            ValidationError: If this would demote the last active Admin.
        """
        current = self.get(user_id)
        name = self._validate.text(data.get("full_name"), "Name")
        role = self._validate.choice(data.get("role"), "Role", ROLES)
        if current.role == ROLE_ADMIN and role != ROLE_ADMIN:
            self._keep_an_admin(current)
        changes = diff_changes({"full_name": current.full_name, "role": current.role},
                               {"full_name": name, "role": role})
        if changes:
            with self._db.transaction():
                self._repo.update_profile(user_id, name, role)
                log_activity(ACTION_UPDATE, ENTITY_USER, user_id, {"changes": changes})
        return self.get(user_id)

    def reset_password(self, user_id: int, password: str) -> None:
        """Set a temporary password that must be changed at next sign-in.

        Args:
            user_id: Account to reset.
            password: Temporary password (password policy applies).
        """
        user = self.get(user_id)
        password_hash = self._auth.policy.hash_new(password, "Temporary password")
        with self._db.transaction():
            self._repo.set_password(user.id, password_hash, must_change=True)
            log_activity(ACTION_UPDATE, ENTITY_USER, user.id,
                         {"changes": {"password": {"old": "***", "new": "reset"}}})

    def set_active(self, user_id: int, active: bool) -> User:
        """Deactivate (cannot sign in) or reactivate an account.

        Args:
            user_id: Account to change.
            active: ``False`` to deactivate, ``True`` to reactivate.

        Returns:
            The updated account.

        Raises:
            ValidationError: When deactivating yourself or the last active Admin.
        """
        user = self.get(user_id)
        if not active:
            if self._auth.current_user and self._auth.current_user.id == user_id:
                raise ValidationError("You cannot deactivate your own account.")
            if user.role == ROLE_ADMIN:
                self._keep_an_admin(user)
        if user.is_active != active:
            with self._db.transaction():
                self._repo.set_active(user_id, active)
                log_activity(ACTION_UPDATE, ENTITY_USER, user_id,
                             {"changes": {"is_active": {"old": user.is_active, "new": active}}})
        return self.get(user_id)

    def _keep_an_admin(self, user: User) -> None:
        """Refuse a change that would leave no active Admin."""
        if user.is_active and self._repo.count_active_admins() <= 1:
            raise ValidationError(f"'{user.username}' is the last active Admin; "
                                  "make another user Admin first.")
