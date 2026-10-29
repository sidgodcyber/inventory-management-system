"""System information for the About / Architecture screen.

The module inventory is discovered at runtime by parsing each source file's
header docstring with :mod:`ast`; nothing is imported or hard-coded. The screen
therefore stays accurate as modules are added, which demonstrates Q11's
"Modular Structure" feature live.

Layer: services
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from config.config_loader import PROJECT_ROOT, AppConfig
from core.database import Database

# (package folder, layer label, responsibility), top layer first.
LAYERS: tuple[tuple[str, str, str], ...] = (
    ("ui", "Presentation", "CustomTkinter windows, views and reusable widgets"),
    ("services", "Business", "Validation, stock rules, analytics, audit logging"),
    ("repositories", "Data access", "All SQL; one repository per table"),
    ("core", "Infrastructure", "Database, logger, settings manager, exceptions"),
    ("models", "Shared models", "Dataclasses passed between layers"),
    ("utils", "Shared helpers", "Validators, formatters, dates, CSV export"),
    ("config", "Configuration", "config.json and its validating loader"),
)

LAYER_DIAGRAM = """\
 ┌──────────────────────────────┐
 │  ui  (views, components)     │   presentation, no SQL
 └──────────────┬───────────────┘
                ▼ calls
 ┌──────────────────────────────┐
 │  services  (business rules)  │   validation, stock, turnover, audit
 └──────────────┬───────────────┘
                ▼ calls
 ┌──────────────────────────────┐
 │  repositories  (SQL only)    │   one class per table
 └──────────────┬───────────────┘
                ▼ calls
 ┌──────────────────────────────┐
 │  core/database  (SQLite)     │   connection, schema, migrations
 └──────────────────────────────┘
   config · core/logger · models · utils  →  usable by every layer"""

LAYER_RULES: tuple[str, ...] = (
    "ui → services → repositories → core/database; nothing imports upward.",
    "SQL appears only in repositories/ (and the schema in core/database.py).",
    "Widgets appear only in ui/; services never import tkinter.",
    "Every tunable value comes from config/config.json or the settings table.",
    "Every create/update/delete/stock/settings action is written via log_activity().",
)


@dataclass
class ModuleInfo:
    """One source module listed on the About screen.

    Attributes:
        layer: Layer label (e.g. ``Business``).
        path: Path relative to the project root.
        summary: First line of the module docstring.
        lines: Number of source lines.
    """

    layer: str
    path: str
    summary: str
    lines: int


class SystemService:
    """Application, database and architecture information.

    Args:
        config: Configuration (app identity, paths).
        db: Database (path and schema version).
    """

    def __init__(self, config: AppConfig, db: Database) -> None:
        self._config = config
        self._db = db

    def app_info(self) -> dict[str, str]:
        """Identity and environment facts shown on the About screen."""
        cfg = self._config
        return {
            "Application": cfg.get("app.name"),
            "Version": cfg.get("app.version"),
            "Course": cfg.get("app.course"),
            "Quality goal": cfg.get("app.quality_goal"),
            "Author": f"{cfg.get('app.author')} ({cfg.get('app.roll_no')})",
            "Database": self._db.path,
            "Schema version": str(self._db.schema_version),
            "Log file": str(cfg.resolve_path("paths.log_file")),
            "Config file": str(cfg.source),
        }

    def modules(self, root: Path = PROJECT_ROOT) -> list[ModuleInfo]:
        """Every Python module in the layered packages, grouped by layer."""
        found: list[ModuleInfo] = []
        for folder, label, _ in LAYERS:
            for path in sorted((root / folder).rglob("*.py")):
                found.append(_describe(path, root, label))
        return found

    @staticmethod
    def layers() -> tuple[tuple[str, str, str], ...]:
        """Layer table: folder, label, responsibility."""
        return LAYERS

    @staticmethod
    def layer_diagram() -> str:
        """Text diagram of the layer stack."""
        return LAYER_DIAGRAM

    @staticmethod
    def layer_rules() -> tuple[str, ...]:
        """The dependency rules the code base follows."""
        return LAYER_RULES


def _describe(path: Path, root: Path, layer: str) -> ModuleInfo:
    """Read a module's docstring summary and line count without importing it."""
    source = path.read_text(encoding="utf-8")
    docstring = ast.get_docstring(ast.parse(source)) or ""
    summary = docstring.strip().splitlines()[0] if docstring.strip() else "(no docstring)"
    return ModuleInfo(layer, path.relative_to(root).as_posix(), summary, len(source.splitlines()))
