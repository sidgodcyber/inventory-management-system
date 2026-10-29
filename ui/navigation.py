"""Screen registry: the sidebar order and which view class renders each screen.

Adding a screen is a two-line change here; the main window, sidebar and
navigation pick it up automatically.

Layer: ui
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

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

#: Sidebar entries in display order: (screen key, label).
NAVIGATION: tuple[tuple[str, str], ...] = (
    ("dashboard", "Dashboard"),
    ("products", "Products"),
    ("categories", "Categories"),
    ("suppliers", "Suppliers"),
    ("stock", "Stock"),
    ("reports", "Reports"),
    ("activity", "Activity Log"),
    ("settings", "Settings"),
    ("about", "About"),
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
    "about": AboutView,
}

#: Screen shown when the application starts.
HOME = "dashboard"
#: Screen whose sidebar button carries the low-stock badge.
BADGE_SCREEN = "products"
