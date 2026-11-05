"""Screen registry: the sidebar order and which view class renders each screen.

Adding a screen is a two-line change here; the main window, sidebar and
navigation pick it up automatically.

Layer: ui
Author: Siddhi Baluja
"""

from __future__ import annotations

from services import permissions as perm
from ui.views.about import AboutView
from ui.views.activity_log import ActivityLogView
from ui.views.base_view import BaseView
from ui.views.categories import CategoriesView
from ui.views.dashboard import DashboardView
from ui.views.products import ProductsView
from ui.views.reports import ReportsView
from ui.views.settings import SettingsView
from ui.views.stock import StockView
from ui.views.suppliers import SuppliersView
from ui.views.users import UsersView

#: Sidebar entries in display order: (screen key, label, permission needed or None).
#: A screen is shown only to roles that hold its permission.
NAVIGATION: tuple[tuple[str, str, str | None], ...] = (
    ("dashboard", "Dashboard", perm.VIEW_REPORTS),
    ("products", "Products", perm.VIEW_REPORTS),
    ("categories", "Categories", perm.MANAGE_CATALOG),
    ("suppliers", "Suppliers", perm.MANAGE_CATALOG),
    ("stock", "Stock", perm.RECORD_STOCK),
    ("reports", "Reports", perm.VIEW_REPORTS),
    ("activity", "Activity Log", perm.VIEW_ACTIVITY),
    ("settings", "Settings", perm.MANAGE_SETTINGS),
    ("users", "Users", perm.MANAGE_USERS),
    ("about", "About", None),
)

#: Screen key -> view class.
VIEW_CLASSES: dict[str, type[BaseView]] = {
    "dashboard": DashboardView,
    "products": ProductsView,
    "categories": CategoriesView,
    "suppliers": SuppliersView,
    "stock": StockView,
    "reports": ReportsView,
    "activity": ActivityLogView,
    "settings": SettingsView,
    "users": UsersView,
    "about": AboutView,
}

#: Screen shown when the application starts.
HOME = "dashboard"
#: Screen whose sidebar button carries the low-stock badge.
BADGE_SCREEN = "products"
