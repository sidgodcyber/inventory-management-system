"""Sign-in, the current session and permission checks.

There is one session per running application (a desktop app). Every audit
entry records the signed-in username, and every protected service method calls
:meth:`AuthService.require` with a permission from :mod:`services.permissions`.

Layer: services
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from config.config_loader import AppConfig
from core.constants import ACTION_CREATE, ACTION_LOGIN, ACTION_UPDATE, ENTITY_USER, ROLE_ADMIN
from core.database import Database
from core.exceptions import AuthenticationError, PermissionDeniedError
from core.logger import log_activity
from models.user import User
from repositories.user_repository import UserRepository
from services.password_policy import PasswordPolicy
from services.permissions import DESCRIPTIONS, permissions_for
from utils.passwords import verify_password
from utils.validators import Validator

_BAD_LOGIN = "Incorrect username or password."
SYSTEM_USER = "system"


class AuthService:
    """Holds the signed-in user and answers "may they do this?".

    Args:
        repo: User repository.
        validator: Field validator (used by the password policy).
        db: Database, used only to open atomic transactions.
        config: Source of the initial admin account and password policy.
    """

    def __init__(self, repo: UserRepository, validator: Validator, db: Database,
                 config: AppConfig) -> None:
        self._repo = repo
        self._db = db
        self._config = config
        self.policy = PasswordPolicy(validator, config)
        self._user: User | None = None

    # -- session ----------------------------------------------------------------------
    @property
    def current_user(self) -> User | None:
        """The signed-in user, or ``None``."""
        return self._user

    def current_username(self) -> str:
        """Username recorded on audit entries (``system`` when nobody is signed in)."""
        return self._user.username if self._user else SYSTEM_USER

    def login(self, username: str, password: str) -> User:
        """Sign in and start a session.

        Args:
            username: Sign-in name (case-insensitive).
            password: Plain-text password (never stored or logged).

        Returns:
            The signed-in user.

        Raises:
            AuthenticationError: For an unknown user, a wrong password or a
                deactivated account (one message for all, so usernames cannot
                be probed). The failure is logged at WARNING level.
        """
        user = self._repo.get_by_username(username or "")
        if user is None or not user.is_active or not verify_password(password or "",
                                                                     user.password_hash):
            log_activity(ACTION_LOGIN, ENTITY_USER, user.id if user else None,
                         {"result": "failed", "username": (username or "").strip()},
                         level="WARNING", user=(username or "").strip() or SYSTEM_USER)
            raise AuthenticationError(_BAD_LOGIN)
        with self._db.transaction():
            self._repo.record_login(user.id)
            log_activity(ACTION_LOGIN, ENTITY_USER, user.id,
                         {"result": "success", "role": user.role}, user=user.username)
        self._user = self._repo.get(user.id)
        return self._user

    def logout(self) -> None:
        """End the session (logged as a LOGIN event with ``result: logout``)."""
        if self._user is not None:
            log_activity(ACTION_LOGIN, ENTITY_USER, self._user.id, {"result": "logout"},
                         user=self._user.username)
        self._user = None

    # -- permissions ------------------------------------------------------------------
    def has(self, permission: str) -> bool:
        """Whether the signed-in user's role grants ``permission``.

        Args:
            permission: A name from :mod:`services.permissions`.

        Returns:
            ``False`` when nobody is signed in.
        """
        return self._user is not None and permission in permissions_for(self._user.role)

    def require(self, permission: str) -> None:
        """Refuse the action unless the signed-in user may perform it.

        Args:
            permission: A name from :mod:`services.permissions`.

        Raises:
            PermissionDeniedError: If nobody is signed in or the role lacks it.
        """
        if self._user is None:
            raise PermissionDeniedError("Please sign in first.")
        if not self.has(permission):
            action = DESCRIPTIONS.get(permission, permission)
            raise PermissionDeniedError(f"The {self._user.role} role is not allowed to {action}.")

    # -- passwords ----------------------------------------------------------------------
    def change_own_password(self, current: str, new: str, confirm: str) -> None:
        """Change the signed-in user's password (clears the must-change flag).

        Args:
            current: Current password.
            new: New password.
            confirm: New password typed again.

        Raises:
            PermissionDeniedError: If nobody is signed in.
            AuthenticationError: If ``current`` is wrong.
            ValidationError: If the new password breaks the policy or does not match.
        """
        if self._user is None:
            raise PermissionDeniedError("Please sign in first.")
        if not verify_password(current or "", self._user.password_hash):
            raise AuthenticationError("Current password is incorrect.")
        self.policy.check_change(current, new, confirm)
        with self._db.transaction():
            self._repo.set_password(self._user.id, self.policy.hash_new(new, "New password"),
                                    must_change=False)
            log_activity(ACTION_UPDATE, ENTITY_USER, self._user.id,
                         {"changes": {"password": {"old": "***", "new": "***"}}})
        self._user = self._repo.get(self._user.id)

    def ensure_initial_admin(self) -> User | None:
        """Create the first Admin from config when the users table is empty.

        Returns:
            The created admin (must change password at first sign-in), or ``None``
            when accounts already exist.
        """
        if self._repo.count():
            return None
        cfg = self._config
        admin = User(username=cfg.get("auth.initial_admin_username"),
                     full_name=cfg.get("auth.initial_admin_full_name"), role=ROLE_ADMIN,
                     password_hash=self.policy.hash_trusted(cfg.get("auth.initial_admin_password")),
                     must_change_password=True)
        with self._db.transaction():
            admin.id = self._repo.create(admin)
            log_activity(ACTION_CREATE, ENTITY_USER, admin.id, {"new": admin.audit_values()},
                         user=SYSTEM_USER)
        return self._repo.get(admin.id)
