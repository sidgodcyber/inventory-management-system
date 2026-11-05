"""Role-based permissions: what each role is allowed to do.

The services check these with ``AuthService.require`` before every write or
restricted read, so the rules hold even if a screen forgets to hide a button.
The UI uses the same names to decide which screens and buttons to show.

Layer: services
Author: Siddhi Baluja
"""

from __future__ import annotations

from core.constants import ROLE_ADMIN, ROLE_MANAGER, ROLE_STAFF

RECORD_STOCK = "record_stock"          # stock in / out / adjust
VIEW_REPORTS = "view_reports"          # dashboard, product list, reports
MANAGE_CATALOG = "manage_catalog"      # add/edit/delete products, categories, suppliers
EXPORT = "export"                      # every CSV export
VIEW_ACTIVITY = "view_activity"        # Activity Log screen
MANAGE_SETTINGS = "manage_settings"    # Settings screen
PURGE_LOG = "purge_log"                # delete old activity entries
MANAGE_USERS = "manage_users"          # Users screen

ALL_PERMISSIONS: frozenset[str] = frozenset({
    RECORD_STOCK, VIEW_REPORTS, MANAGE_CATALOG, EXPORT, VIEW_ACTIVITY, MANAGE_SETTINGS,
    PURGE_LOG, MANAGE_USERS,
})

_STAFF: frozenset[str] = frozenset({RECORD_STOCK, VIEW_REPORTS})
_MANAGER: frozenset[str] = _STAFF | {MANAGE_CATALOG, EXPORT, VIEW_ACTIVITY}

#: Role -> permissions granted (Admin > Store Manager > Store Staff).
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    ROLE_ADMIN: ALL_PERMISSIONS,
    ROLE_MANAGER: _MANAGER,
    ROLE_STAFF: _STAFF,
}

#: Short description of each permission (used in messages and documentation).
DESCRIPTIONS: dict[str, str] = {
    RECORD_STOCK: "record stock movements",
    VIEW_REPORTS: "view the dashboard and reports",
    MANAGE_CATALOG: "add, edit or delete products, categories and suppliers",
    EXPORT: "export data to CSV",
    VIEW_ACTIVITY: "view the activity log",
    MANAGE_SETTINGS: "change system settings",
    PURGE_LOG: "purge the activity log",
    MANAGE_USERS: "manage user accounts",
}


def permissions_for(role: str) -> frozenset[str]:
    """Permissions granted to a role.

    Args:
        role: One of ``core.constants.ROLES``.

    Returns:
        The role's permissions (empty for an unknown role).
    """
    return ROLE_PERMISSIONS.get(role, frozenset())
