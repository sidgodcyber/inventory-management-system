"""Users screen (Admin only): add accounts, change roles, reset passwords, (de)activate.

Accounts are never deleted, so the audit trail always resolves to a real
user; deactivated accounts simply cannot sign in.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

from core.constants import ROLE_STAFF, ROLES
from models.common import ListQuery, Page
from models.user import User
from services.permissions import MANAGE_USERS
from ui.components.confirm_dialog import ask_confirm
from ui.components.data_table import TAG_INACTIVE, Column, Row
from ui.components.form_dialog import COMBO, FormDialog, FormField
from ui.views.crud_view import CrudView


class UsersView(CrudView):
    """Account management for administrators."""

    title = "Users"
    subtitle = ("Admin: everything · Store Manager: catalog, stock, reports, activity log · "
                "Store Staff: stock movements, products and reports (view only).")
    entity = "User"
    manage_permission = MANAGE_USERS
    default_sort = "username"
    search_hint = "Search username, name or role…"
    columns = (
        Column("username", "Username", 140), Column("full_name", "Name", 220),
        Column("role", "Role", 140), Column("is_active", "Status", 90, "center"),
        Column("last_login_at", "Last sign-in", 160),
    )

    def add_buttons(self) -> None:
        """Activate/deactivate, reset password, edit and add (accounts are never deleted)."""
        if not self.can(MANAGE_USERS):
            return
        self.toolbar.add_button("Activate / Deactivate", self._toggle_active, "secondary", 160)
        self.toolbar.add_button("Reset password", self._reset_password, "secondary", 130)
        self.toolbar.add_button("Edit", self._edit_selected, "secondary", width=80)
        self.toolbar.add_button("+ Add user", self._add, width=120)

    def fetch(self, query: ListQuery) -> Page[User]:
        """One page of accounts (see :meth:`ListView.fetch`)."""
        return self.services.users.find(query)

    def to_row(self, item: User) -> Row:
        """Table row; inactive accounts in grey.

        Args:
            item: Account to display.

        Returns:
            ``(row id, values, tags)``.
        """
        values = (item.username, item.full_name, item.role,
                  "Active" if item.is_active else "Inactive",
                  self.datetime_text(item.last_login_at) if item.last_login_at else "Never")
        return str(item.id), values, () if item.is_active else (TAG_INACTIVE,)

    def load(self, item_id: int) -> User:
        """Account to edit (see :meth:`CrudView.load`)."""
        return self.services.users.get(item_id)

    def form_fields(self, item: Any | None) -> list[FormField]:
        """Add form asks for username and initial password; edit only name and role.

        Args:
            item: ``None`` when adding, otherwise the account being edited.

        Returns:
            Field definitions.
        """
        fields = [FormField("full_name", "Name", required=True),
                  FormField("role", "Role", COMBO, list(ROLES), required=True)]
        if item is None:
            minimum = self.services.config.get("auth.min_password_length")
            fields = [FormField("username", "Username", required=True), *fields,
                      FormField("password", "Initial password", required=True, secret=True,
                                hint=f"At least {minimum} characters; changed at first sign-in")]
        return fields

    def initial_values(self, item: Any | None) -> dict[str, Any]:
        """New accounts default to Store Staff (see :meth:`CrudView.initial_values`)."""
        return {"role": ROLE_STAFF} if item is None else dict(vars(item))

    def save(self, values: dict[str, str], item_id: int | None) -> User:
        """Create or update through the user service (see :meth:`CrudView.save`)."""
        if item_id is None:
            return self.services.users.create(values)
        return self.services.users.update(item_id, values)

    def _reset_password(self) -> None:
        """Ask for a temporary password for the selected account."""
        row_id = self._require_selection("reset")
        if not row_id:
            return
        username = self.table.row_values(row_id)[0]
        FormDialog(self, self.theme, f"Reset password for {username}",
                   [FormField("password", "Temporary password", required=True, secret=True,
                              hint="The user must change it at next sign-in")],
                   on_submit=lambda values: self.form_call(
                       "Users > Reset password",
                       lambda: self.services.users.reset_password(int(row_id), values["password"]),
                       lambda _r: self.notify(f"Password reset for {username}.", "success")),
                   submit_text="Reset")

    def _toggle_active(self) -> None:
        """Deactivate (after confirmation) or reactivate the selected account."""
        row_id = self._require_selection("activate or deactivate")
        user = row_id and self.guarded("Users > Open", lambda: self.load(int(row_id)))
        if not user:
            return
        if user.is_active and not ask_confirm(
                self, self.theme, "Deactivate user",
                f"Deactivate '{user.username}'? They will no longer be able to sign in.",
                "Deactivate", danger=True):
            return
        if self.guarded("Users > Activate/Deactivate",
                        lambda: self.services.users.set_active(user.id, not user.is_active)):
            self.notify(f"{user.username} {'deactivated' if user.is_active else 'reactivated'}.",
                        "success")
            self.load_page()
