"""Helpers for the signed-in session: role-filtered sidebar and status-bar text.

Layer: ui
Author: Siddhi Baluja
"""

from __future__ import annotations

from collections.abc import Callable

from config.config_loader import PROJECT_ROOT
from services.container import AppServices
from ui.components.sidebar import Sidebar
from ui.navigation import BADGE_SCREEN, NAVIGATION
from ui.theme import Theme


def allowed_screens(services: AppServices) -> list[tuple[str, str]]:
    """Sidebar entries the signed-in user's role may open.

    Args:
        services: Service container (permission checks).

    Returns:
        ``(screen key, label)`` pairs in display order.
    """
    return [(key, label) for key, label, permission in NAVIGATION
            if permission is None or services.auth.has(permission)]


def build_sidebar(master: object, theme: Theme, services: AppServices,
                  on_select: Callable[[str], None], on_change_password: Callable[[], None],
                  on_sign_out: Callable[[], None]) -> Sidebar:
    """Create the role-filtered sidebar with the account footer.

    Args:
        master: Main window.
        theme: Shared theme.
        services: Service container (config, current user, permissions).
        on_select: Called with a screen key.
        on_change_password: "Change password" handler.
        on_sign_out: "Sign out" handler.

    Returns:
        The sidebar (not yet placed in the grid).
    """
    cfg, user = services.config, services.auth.current_user
    sidebar = Sidebar(master, theme, cfg.get("app.short_name"), cfg.get("app.tagline"),
                      cfg.get("ui.sidebar_width"), allowed_screens(services), on_select)
    sidebar.add_account_footer(f"{user.full_name}\n{user.username} · {user.role}",
                               on_change_password, on_sign_out)
    return sidebar


def status_text(services: AppServices) -> str:
    """Right-hand status-bar text: signed-in user, database path and version.

    Args:
        services: Service container.

    Returns:
        The text to display.
    """
    user = services.auth.current_user
    who = f"Signed in: {user.username} ({user.role})" if user else "Not signed in"
    db_path = services.db.path
    try:
        db_path = str(PROJECT_ROOT.joinpath(db_path).relative_to(PROJECT_ROOT))
    except ValueError:
        pass  # database outside the project folder: show the full path
    return f"{who}   ·   DB: {db_path}   ·   v{services.config.get('app.version')}"


def destroy_widgets(views: dict[str, object], *widgets: object) -> None:
    """Destroy cached screens and other session widgets (``None`` entries are skipped).

    Args:
        views: Cached screens by key; emptied afterwards.
        *widgets: Further widgets such as the sidebar or the sign-in form.
    """
    for widget in [*views.values(), *widgets]:
        if widget is not None:
            widget.destroy()
    views.clear()


def refresh_badge(sidebar: Sidebar | None, services: AppServices) -> None:
    """Show the low-stock count on the Products button (no-op before sign-in).

    Args:
        sidebar: The current sidebar, or ``None`` while nobody is signed in.
        services: Service container (low-stock count).
    """
    if sidebar is not None:
        sidebar.set_badge(BADGE_SCREEN, services.products.low_stock_count())
