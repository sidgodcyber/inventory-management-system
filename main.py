"""Entry point: load config, initialise the database, launch the UI.

Start-up sequence:

1. Load and validate ``config/config.json``; a broken file stops with a clear message.
2. Open the SQLite database and run pending schema migrations.
3. Build services (seeds runtime settings from config on first run).
4. Configure the rotating file log at the saved log level.
5. Record a ``LOGIN`` activity entry and open the main window.

Layer: entry point (composition only, no business logic)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import sys

from config.config_loader import ConfigError, load_config
from core.database import Database
from core.logger import get_logger, setup_file_logging
from services.container import build_services


def _fail(message: str) -> int:
    """Report a fatal start-up problem on the console and in a dialog."""
    print(message, file=sys.stderr)
    try:
        from tkinter import Tk, messagebox

        root = Tk()
        root.withdraw()
        messagebox.showerror("Cannot start", message)
        root.destroy()
    except Exception:  # noqa: BLE001 - no display available; console message is enough
        pass
    return 1


def main() -> int:
    """Start the application.

    Returns:
        Process exit code.
    """
    try:
        config = load_config()
    except ConfigError as exc:
        return _fail(str(exc))
    db = Database(config.resolve_path("paths.database"))
    db.initialize()
    services = build_services(config, db)
    setup_file_logging(config)
    services.settings.apply_startup()  # saved log level overrides the config default
    get_logger("main").info("Starting %s v%s", config.get("app.name"), config.get("app.version"))
    services.activity.record_login()

    from ui.app import App  # imported late so config errors show before Tk loads

    App(services).mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
