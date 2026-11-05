"""Tests that each role is offered exactly the screens it may open.

Layer: tests
Author: Siddhi Baluja
"""

from __future__ import annotations

import pytest

from core.constants import ROLE_ADMIN, ROLE_MANAGER, ROLE_STAFF
from services.container import AppServices
from ui.navigation import NAVIGATION, VIEW_CLASSES
from ui.session import allowed_screens, status_text

PASSWORD = "Str0ng-pass"
EXPECTED = {
    ROLE_STAFF: ["dashboard", "products", "stock", "reports", "about"],
    ROLE_MANAGER: ["dashboard", "products", "categories", "suppliers", "stock", "reports",
                   "activity", "about"],
    ROLE_ADMIN: [key for key, _, _ in NAVIGATION],
}


@pytest.mark.parametrize("role", EXPECTED)
def test_sidebar_matches_role(services: AppServices, role: str) -> None:
    """The sidebar lists the role's screens, in display order."""
    services.users.create({"username": "someone", "full_name": "Some One", "role": role,
                           "password": PASSWORD})
    services.auth.logout()
    services.auth.login("someone", PASSWORD)
    assert [key for key, _ in allowed_screens(services)] == EXPECTED[role]
    assert f"someone ({role})" in status_text(services)


def test_every_navigation_entry_has_a_view() -> None:
    """A screen cannot be listed without an implementation."""
    assert {key for key, _, _ in NAVIGATION} == set(VIEW_CLASSES)


def test_status_text_when_signed_out(services: AppServices) -> None:
    """Before sign-in the status bar says so."""
    services.auth.logout()
    assert "Not signed in" in status_text(services)
