"""Tests for sign-in, role permissions and user management.

Layer: tests
Author: Siddhi Baluja
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config.config_loader import AppConfig
from core.constants import ROLE_ADMIN, ROLE_MANAGER, ROLE_STAFF
from core.exceptions import AuthenticationError, PermissionDeniedError, ValidationError
from models.common import ListQuery
from models.filters import ActivityFilter
from services import permissions as perm
from services.container import AppServices

PASSWORD = "Str0ng-pass"


def _make_user(services: AppServices, username: str, role: str) -> int:
    """Create an account (as the signed-in admin) and return its id."""
    data = {"username": username, "full_name": username.title(), "role": role,
            "password": PASSWORD}
    return services.users.create(data).id


def _sign_in_as(services: AppServices, username: str) -> None:
    """End the current session and sign in as ``username``."""
    services.auth.logout()
    services.auth.login(username, PASSWORD)


def _logins(services: AppServices, result: str) -> list:
    """LOGIN entries with the given result (as the admin sees them)."""
    page = services.activity.find(ActivityFilter(action="LOGIN"), ListQuery(page_size=100))
    return [e for e in page.items if e.details.get("result") == result]


# -- sign-in --------------------------------------------------------------------------
def test_initial_admin_must_change_password(services: AppServices, config: AppConfig) -> None:
    """The bootstrap admin exists, is signed in and must pick a new password."""
    user = services.auth.current_user
    assert (user.username, user.role) == (config.get("auth.initial_admin_username"), ROLE_ADMIN)
    assert user.must_change_password and user.last_login_at
    assert _logins(services, "success")


@pytest.mark.parametrize(("username", "password"), [("admin", "wrong"), ("ghost", PASSWORD),
                                                    ("", "")])
def test_bad_login_refused_and_logged(services: AppServices, username: str,
                                      password: str) -> None:
    """Wrong password, unknown user or blank fields give one generic message."""
    with pytest.raises(AuthenticationError, match="Incorrect username or password"):
        services.auth.login(username, password)
    failed = _logins(services, "failed")
    assert failed and failed[0].level == "WARNING" and "password" not in failed[0].details


def test_deactivated_user_cannot_sign_in(services: AppServices) -> None:
    """Inactive accounts are refused."""
    staff_id = _make_user(services, "asha", ROLE_STAFF)
    services.users.set_active(staff_id, False)
    with pytest.raises(AuthenticationError):
        services.auth.login("asha", PASSWORD)


def test_change_own_password(services: AppServices, config: AppConfig) -> None:
    """Changing the password clears the must-change flag and needs the current one."""
    initial = config.get("auth.initial_admin_password")
    with pytest.raises(AuthenticationError):
        services.auth.change_own_password("nope", PASSWORD, PASSWORD)
    with pytest.raises(ValidationError, match="do not match"):
        services.auth.change_own_password(initial, PASSWORD, PASSWORD + "x")
    with pytest.raises(ValidationError, match="at least"):
        services.auth.change_own_password(initial, "short", "short")
    services.auth.change_own_password(initial, PASSWORD, PASSWORD)
    assert not services.auth.current_user.must_change_password
    services.auth.logout()
    assert services.auth.login("admin", PASSWORD).username == "admin"


# -- permissions ----------------------------------------------------------------------
def test_permission_matrix() -> None:
    """Admin > Store Manager > Store Staff."""
    admin, manager, staff = (perm.permissions_for(r) for r in (ROLE_ADMIN, ROLE_MANAGER,
                                                               ROLE_STAFF))
    assert staff == {perm.RECORD_STOCK, perm.VIEW_REPORTS}
    assert staff < manager < admin == perm.ALL_PERMISSIONS
    assert perm.MANAGE_SETTINGS not in manager and perm.MANAGE_USERS not in manager


def test_staff_limits_enforced_by_services(services: AppServices, tmp_path: Path) -> None:
    """Staff can record stock but not edit the catalog, export, configure or audit."""
    category = services.categories.create("General")
    product = services.products.create({"sku": "GEN-1", "name": "Widget",
                                        "category_id": category.id, "unit": "pcs",
                                        "unit_cost": "5", "selling_price": "8",
                                        "reorder_level": "2", "opening_quantity": "10"}).product
    _make_user(services, "asha", ROLE_STAFF)
    _sign_in_as(services, "asha")
    result = services.stock.stock_out(product.id, 3)
    assert result.transaction.performed_by == "asha"
    refused = [lambda: services.categories.create("Toys"),
               lambda: services.products.export_csv(path=tmp_path / "p.csv"),
               lambda: services.settings.save({"page_size": "20"}),
               lambda: services.activity.find(ActivityFilter(), ListQuery()),
               lambda: services.users.find(ListQuery())]
    for action in refused:
        with pytest.raises(PermissionDeniedError, match="Store Staff"):
            action()


def test_manager_cannot_manage_users_or_settings(services: AppServices) -> None:
    """Managers edit the catalog but not users, settings or the purge."""
    _make_user(services, "ravi", ROLE_MANAGER)
    _sign_in_as(services, "ravi")
    assert services.categories.create("Toys").name == "Toys"
    for action in (lambda: services.users.find(ListQuery()),
                   lambda: services.settings.save({"page_size": "20"}),
                   services.activity.purge_expired):
        with pytest.raises(PermissionDeniedError):
            action()


def test_signed_out_user_is_refused(services: AppServices) -> None:
    """Nothing protected works without a session."""
    services.auth.logout()
    with pytest.raises(PermissionDeniedError, match="sign in"):
        services.categories.create("Toys")


# -- user management ------------------------------------------------------------------
def test_create_user_rules(services: AppServices) -> None:
    """Usernames are unique, roles are fixed and the password policy applies."""
    _make_user(services, "asha", ROLE_STAFF)
    bad = [{"username": "ASHA", "full_name": "A", "role": ROLE_STAFF, "password": PASSWORD},
           {"username": "bob", "full_name": "B", "role": "Owner", "password": PASSWORD},
           {"username": "cat", "full_name": "C", "role": ROLE_STAFF, "password": "123"}]
    for data in bad:
        with pytest.raises(ValidationError):
            services.users.create(data)


def test_last_admin_and_self_protection(services: AppServices) -> None:
    """You cannot lock everyone out of user management."""
    admin_id = services.auth.current_user.id
    with pytest.raises(ValidationError, match="your own account"):
        services.users.set_active(admin_id, False)
    with pytest.raises(ValidationError, match="last active Admin"):
        services.users.update(admin_id, {"full_name": "Admin", "role": ROLE_STAFF})
    second = _make_user(services, "boss", ROLE_ADMIN)
    services.users.update(admin_id, {"full_name": "Admin", "role": ROLE_MANAGER})
    assert services.users.get(second).role == ROLE_ADMIN


def test_reset_password_forces_change_and_is_audited(services: AppServices) -> None:
    """A reset sets a temporary password; the hash never appears in the log."""
    staff_id = _make_user(services, "asha", ROLE_STAFF)
    services.users.reset_password(staff_id, "Temp-pass-1")
    assert services.users.get(staff_id).must_change_password
    entries = services.activity.find(ActivityFilter(entity="User"), ListQuery(page_size=100))
    assert all("pbkdf2" not in e.details_json for e in entries.items)
    services.auth.logout()
    assert services.auth.login("asha", "Temp-pass-1").must_change_password
