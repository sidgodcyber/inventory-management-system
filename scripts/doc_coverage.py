"""Measure docstring and type-hint coverage of the application source (QO5).

Counts, with :mod:`ast` (no imports, no side effects):

* **modules** with a header docstring,
* **classes** with a docstring,
* **public functions and methods** (names not starting with ``_``) with a docstring,
* **type hints**: every function (public or private) whose parameters other than
  ``self``/``cls`` and whose return value are annotated.

Writes its section of ``docs/quality_report.md`` between the
``DOC_COVERAGE`` markers (``scripts/quality_report.py`` regenerates the whole
file and embeds this section). Exit code is 1 when coverage is below 100%.

Usage::

    python scripts/doc_coverage.py

Layer: scripts (tooling, not shipped in the app)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Application code (judged for QO5 and QO6) and developer tooling (QO5 only).
SOURCE_DIRS: tuple[str, ...] = ("config", "core", "models", "repositories", "services", "ui",
                                "utils")
SOURCE_FILES: tuple[str, ...] = ("main.py",)
TOOLING_DIRS: tuple[str, ...] = ("scripts",)
REPORT_PATH = PROJECT_ROOT / "docs" / "quality_report.md"
START_MARK = "<!-- DOC_COVERAGE:START -->"
END_MARK = "<!-- DOC_COVERAGE:END -->"
TARGET = 100.0


@dataclass
class Counter:
    """Documented / total pair."""

    done: int = 0
    total: int = 0

    def add(self, ok: bool) -> None:
        """Count one item."""
        self.total += 1
        self.done += int(ok)

    @property
    def percent(self) -> float:
        """Coverage percentage (100 when there is nothing to count)."""
        return 100.0 * self.done / self.total if self.total else 100.0

    def merge(self, other: Counter) -> None:
        """Add another counter's numbers to this one."""
        self.done += other.done
        self.total += other.total


@dataclass
class FileCoverage:
    """Coverage numbers for one source file."""

    path: str
    modules: Counter = field(default_factory=Counter)
    classes: Counter = field(default_factory=Counter)
    functions: Counter = field(default_factory=Counter)
    hints: Counter = field(default_factory=Counter)
    missing: list[str] = field(default_factory=list)


def source_files(root: Path = PROJECT_ROOT) -> list[Path]:
    """Every Python file that belongs to the application (packages + ``main.py``)."""
    files = [p for folder in SOURCE_DIRS for p in sorted((root / folder).rglob("*.py"))]
    return files + [root / name for name in SOURCE_FILES if (root / name).exists()]


def tooling_files(root: Path = PROJECT_ROOT) -> list[Path]:
    """Developer scripts: documented like the app, but not part of the shipped system."""
    return [p for folder in TOOLING_DIRS for p in sorted((root / folder).rglob("*.py"))]


def _fully_annotated(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True when every parameter (except self/cls) and the return are annotated."""
    args = node.args
    params = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    params = [a for a in params if a.arg not in ("self", "cls")]
    params += [a for a in (args.vararg, args.kwarg) if a is not None]
    return node.returns is not None and all(a.annotation is not None for a in params)


def _is_public(name: str) -> bool:
    """Public API: no leading underscore (dunder methods are covered by the class)."""
    return not name.startswith("_")


def analyse(path: Path, root: Path = PROJECT_ROOT) -> FileCoverage:
    """Count docstrings and annotations in one file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result = FileCoverage(path.relative_to(root).as_posix())
    result.modules.add(bool(ast.get_docstring(tree)))
    if not ast.get_docstring(tree):
        result.missing.append("module docstring")
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            _count(result, result.classes, node, f"class {node.name}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_public(node.name):
                _count(result, result.functions, node, f"def {node.name}")
            annotated = _fully_annotated(node)
            result.hints.add(annotated)
            if not annotated:
                result.missing.append(f"type hints on {node.name} (line {node.lineno})")
    return result


def _count(result: FileCoverage, counter: Counter, node: ast.AST, label: str) -> None:
    """Record whether ``node`` has a docstring."""
    documented = bool(ast.get_docstring(node))
    counter.add(documented)
    if not documented:
        result.missing.append(f"docstring for {label} (line {node.lineno})")


def totals(results: list[FileCoverage]) -> FileCoverage:
    """Sum every file's counters."""
    total = FileCoverage("TOTAL")
    for item in results:
        for name in ("modules", "classes", "functions", "hints"):
            getattr(total, name).merge(getattr(item, name))
    return total


def passes(total: FileCoverage) -> bool:
    """QO5: 100% docstrings for modules, classes and public functions; 100% hints."""
    return all(getattr(total, name).percent >= TARGET
               for name in ("modules", "classes", "functions", "hints"))


def render(results: list[FileCoverage]) -> str:
    """Markdown section with totals, verdict and any gaps."""
    total = totals(results)
    verdict = "✅ PASS" if passes(total) else "❌ FAIL"
    lines = [
        START_MARK,
        "## QO5: Documented code (docstrings and type hints)",
        "",
        f"**Verdict: {verdict}** (target: {TARGET:.0f}% for every row)",
        "",
        "| Item | Documented | Total | Coverage |",
        "|------|-----------:|------:|---------:|",
    ]
    for label, name in (("Modules (header docstring)", "modules"), ("Classes", "classes"),
                        ("Public functions & methods", "functions"),
                        ("Functions fully type-hinted", "hints")):
        counter = getattr(total, name)
        lines.append(f"| {label} | {counter.done} | {counter.total} | {counter.percent:.1f}% |")
    gaps = [(r.path, gap) for r in results for gap in r.missing]
    lines += ["", f"Files analysed: {len(results)}. Gaps found: {len(gaps)}.", ""]
    lines += [f"- `{path}`: missing {gap}" for path, gap in gaps]
    lines.append(END_MARK)
    return "\n".join(lines)


def write_section(section: str, report: Path = REPORT_PATH) -> None:
    """Replace (or append) the doc-coverage section of the report file."""
    report.parent.mkdir(parents=True, exist_ok=True)
    text = report.read_text(encoding="utf-8") if report.exists() else "# Quality report\n"
    if START_MARK in text and END_MARK in text:
        before, rest = text.split(START_MARK, 1)
        text = before + section + rest.split(END_MARK, 1)[1]
    else:
        text = f"{text.rstrip()}\n\n{section}\n"
    report.write_text(text, encoding="utf-8")


def run() -> tuple[list[FileCoverage], FileCoverage]:
    """Analyse every source file and return per-file results and totals."""
    results = [analyse(path) for path in source_files() + tooling_files()]
    return results, totals(results)


def main() -> int:
    """Print a summary, update the report and return the exit code."""
    sys.stdout.reconfigure(encoding="utf-8")
    results, total = run()
    write_section(render(results))
    for name in ("modules", "classes", "functions", "hints"):
        counter = getattr(total, name)
        print(f"{name:<10} {counter.done:>4}/{counter.total:<4} {counter.percent:6.1f}%")
    print(f"QO5 {'PASS' if passes(total) else 'FAIL'}; report: {REPORT_PATH}")
    return 0 if passes(total) else 1


if __name__ == "__main__":
    raise SystemExit(main())
