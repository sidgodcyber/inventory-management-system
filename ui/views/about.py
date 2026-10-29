"""About / Architecture screen: shows the modular structure live (Q11 feature 1).

The module list is discovered at runtime from each file's header docstring
(``SystemService.modules``), so this screen proves the layering and
documentation of the actual code base, not a hand-maintained copy.

Layer: ui/views
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ui.components.data_table import Column, DataTable
from ui.views.base_view import BaseView

# Where each Q11 maintainability feature lives in the code base.
Q11_FEATURES: tuple[tuple[str, str], ...] = (
    ("1. Modular Structure", "Layered packages ui → services → repositories → core; "
                             "this screen lists every module."),
    ("2. Config Files", "config/config.json validated by config/config_loader.py at start-up."),
    ("3. System Settings", "Settings screen → settings table (seeded from config.json), "
                           "applied live, audited."),
    ("4. Activity Logs", "logs/app.log (rotating) + activity_log table via "
                         "core/logger.log_activity()."),
    ("5. Code Comments", "Header, class and function docstrings with type hints; "
                         "measured by scripts/doc_coverage.py."),
)


class AboutView(BaseView):
    """Application identity, architecture diagram, rules and module inventory."""

    title = "About / Architecture"
    subtitle = "How the system is organised for maintainability (TQM quality goal Q11)."

    def build(self) -> None:
        """Two tabs: overview and module inventory."""
        tabs = ctk.CTkTabview(self.body)
        tabs.pack(fill="both", expand=True)
        self._build_overview(tabs.add("Overview"))
        self._build_modules(tabs.add("Modules"))

    def _build_overview(self, tab: Any) -> None:
        """Identity facts and Q11 map on the left, diagram and rules on the right."""
        tab.grid_columnconfigure((0, 1), weight=1, uniform="about")
        tab.grid_rowconfigure(0, weight=1)
        left = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._fact_rows(left, "Application", self.services.system.app_info().items())
        self._fact_rows(left, "Q11 maintainability features", Q11_FEATURES)
        right = ctk.CTkFrame(tab, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._section(right, "Layer diagram")
        diagram = ctk.CTkTextbox(right, height=250, font=self.theme.mono_font(), wrap="none")
        diagram.pack(fill="x")
        diagram.insert("1.0", self.services.system.layer_diagram())
        diagram.configure(state="disabled")
        self._section(right, "Layer rules")
        rules = "\n".join(f"•  {rule}" for rule in self.services.system.layer_rules())
        ctk.CTkLabel(right, text=rules, justify="left", anchor="w", wraplength=480,
                     font=self.theme.font(-1)).pack(fill="x")

    def _fact_rows(self, parent: Any, heading: str, rows: Any) -> None:
        """Heading followed by label/value pairs."""
        self._section(parent, heading)
        for label, value in rows:
            line = ctk.CTkFrame(parent, fg_color="transparent")
            line.pack(fill="x", pady=1)
            ctk.CTkLabel(line, text=label, width=170, anchor="nw", font=self.theme.font(-1, "bold"),
                         ).pack(side="left", anchor="n")
            ctk.CTkLabel(line, text=str(value), anchor="w", justify="left", wraplength=340,
                         font=self.theme.font(-1)).pack(side="left", fill="x", expand=True)

    def _section(self, parent: Any, text: str) -> None:
        """Bold section heading."""
        ctk.CTkLabel(parent, text=text, font=self.theme.font(2, "bold"), anchor="w").pack(
            fill="x", pady=(8, 4))

    def _build_modules(self, tab: Any) -> None:
        """Every module with its layer, size and docstring summary."""
        self.module_count = ctk.CTkLabel(tab, text="", anchor="w", font=self.theme.font(-1))
        self.module_count.pack(fill="x", pady=(0, 6))
        columns = (Column("layer", "Layer", 120, sortable=False),
                   Column("path", "Module", 300, sortable=False),
                   Column("lines", "Lines", 70, "e", sortable=False),
                   Column("summary", "Purpose (first docstring line)", 560, sortable=False))
        self.module_table = DataTable(tab, self.theme, columns, height=14)
        self.module_table.pack(fill="both", expand=True)

    def refresh(self) -> None:
        """Re-scan the source tree (cheap: docstrings only)."""
        modules = self.guarded("About > Modules", self.services.system.modules)
        if modules is None:
            return
        layers = len({m.layer for m in modules})
        total = sum(m.lines for m in modules)
        self.module_count.configure(
            text=f"{len(modules)} modules in {layers} layers · {total:,} lines of Python")
        self.module_table.set_rows(
            (m.path, (m.layer, m.path, m.lines, m.summary), ()) for m in modules)
