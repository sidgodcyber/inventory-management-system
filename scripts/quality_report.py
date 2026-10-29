"""Generate ``docs/quality_report.md``: radon complexity/maintainability + doc coverage.

Measures, for every application source file:

* **Cyclomatic complexity (CC)** per function/method with radon; the report shows
  the average and the worst function per file. **QO6 target:** overall average
  CC grade A (≤ 5).
* **Maintainability index (MI)** per file (radon, multi-line strings counted as
  comments). **QO6 target:** MI ≥ 65 for *every* file.
* **Docstring and type-hint coverage** via :mod:`scripts.doc_coverage` (**QO5**).
* Optionally the **pytest** result (**QO7**) with ``--tests``.

Usage::

    python scripts/quality_report.py            # radon + doc coverage
    python scripts/quality_report.py --tests    # also run pytest and record the result

Layer: scripts (tooling, not shipped in the app)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from radon.complexity import cc_rank, cc_visit
from radon.metrics import mi_rank, mi_visit
from radon.visitors import Function

sys.path.insert(0, str(Path(__file__).resolve().parent))
import doc_coverage  # noqa: E402  (sibling script)

PROJECT_ROOT = doc_coverage.PROJECT_ROOT
REPORT_PATH = doc_coverage.REPORT_PATH
CC_TARGET = 5.0     # average CC must be grade A
MI_TARGET = 65.0    # every file's maintainability index
CC_FLAG = 10        # functions above this are listed as refactoring candidates


@dataclass
class FileMetrics:
    """radon results for one file."""

    path: str
    functions: int
    average_cc: float
    worst_name: str
    worst_cc: int
    mi: float
    lines: int

    @property
    def mi_ok(self) -> bool:
        """True when the file meets the MI target."""
        return self.mi >= MI_TARGET


def measure(path: Path) -> FileMetrics:
    """Run radon CC and MI on one file."""
    code = path.read_text(encoding="utf-8")
    blocks = [b for b in cc_visit(code) if isinstance(b, Function)]
    worst = max(blocks, key=lambda b: b.complexity, default=None)
    average = sum(b.complexity for b in blocks) / len(blocks) if blocks else 0.0
    return FileMetrics(
        path=path.relative_to(PROJECT_ROOT).as_posix(),
        functions=len(blocks),
        average_cc=average,
        worst_name=worst.fullname if worst else "-",
        worst_cc=worst.complexity if worst else 0,
        mi=mi_visit(code, multi=True),
        lines=len(code.splitlines()),
    )


def overall_cc(metrics: list[FileMetrics]) -> float:
    """Average CC across every function in every file (weighted by function count)."""
    count = sum(m.functions for m in metrics)
    return sum(m.average_cc * m.functions for m in metrics) / count if count else 0.0


def run_tests() -> str:
    """Run pytest quietly and return its summary line."""
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-o", "addopts="],
                            cwd=PROJECT_ROOT,
                            capture_output=True, text=True, encoding="utf-8")
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    summary = lines[-1] if lines else "pytest produced no output"
    return re.sub(r"=+", "", summary).strip()


def render(metrics: list[FileMetrics], tooling: list[FileMetrics],
           test_summary: str | None) -> str:
    """Whole report as Markdown (doc-coverage section appended by the caller)."""
    avg_cc = overall_cc(metrics)
    avg_mi = sum(m.mi for m in metrics) / len(metrics)
    failing_mi = [m for m in metrics if not m.mi_ok]
    cc_ok, mi_ok = avg_cc <= CC_TARGET, not failing_mi
    lines = [
        "# Quality report: maintainability evidence (Q11)",
        "",
        f"Generated {datetime.now():%Y-%m-%d %H:%M} by `scripts/quality_report.py` "
        f"(radon CC + MI, docstring coverage). **Do not edit by hand.**",
        "",
        "Scope: QO6 is judged on the application (`config`, `core`, `models`, "
        "`repositories`, `services`, `ui`, `utils`, `main.py`). Developer tooling in "
        "`scripts/` is listed for information; QO5 covers both.",
        "",
        "## Summary",
        "",
        "| Objective | Measure | Target | Result | Verdict |",
        "|-----------|---------|--------|--------|---------|",
        f"| QO6 | Average cyclomatic complexity | ≤ {CC_TARGET:.0f} (grade A) | "
        f"{avg_cc:.2f} (grade {cc_rank(round(avg_cc))}) | {_verdict(cc_ok)} |",
        f"| QO6 | Maintainability index, every file | ≥ {MI_TARGET:.0f} | "
        f"min {min(m.mi for m in metrics):.1f}, avg {avg_mi:.1f} | {_verdict(mi_ok)} |",
    ]
    _, doc_total = doc_coverage.run()
    lines.append(f"| QO5 | Docstrings + type hints | 100% | "
                 f"{min(getattr(doc_total, n).percent for n in ('modules', 'classes', 'functions', 'hints')):.1f}% "
                 f"(lowest category) | {_verdict(doc_coverage.passes(doc_total))} |")
    if test_summary is not None:
        tests_ok = "failed" not in test_summary and "error" not in test_summary
        lines.append(f"| QO7 | pytest (repositories, services, utils, config, core) | "
                     f"all pass | {test_summary} | {_verdict(tests_ok)} |")
    lines += ["", f"Files analysed: {len(metrics)} · functions/methods: "
                  f"{sum(m.functions for m in metrics)} · lines: {sum(m.lines for m in metrics):,}",
              ""]
    lines += _file_table(metrics, "## QO6: Complexity and maintainability per application file")
    lines += _hotspots(metrics)
    lines += _file_table(tooling, "## Developer tooling (informational, not judged)")
    return "\n".join(lines)


def _verdict(ok: bool) -> str:
    """Pass/fail badge."""
    return "✅ PASS" if ok else "❌ FAIL"


def _file_table(metrics: list[FileMetrics], heading: str) -> list[str]:
    """Per-file radon table under ``heading``."""
    lines = [heading, "",
             "| File | Lines | Funcs | Avg CC | Worst function (CC) | MI | MI rank |",
             "|------|------:|------:|-------:|---------------------|---:|:-------:|"]
    for m in metrics:
        flag = "" if m.mi_ok else " ⚠"
        lines.append(f"| `{m.path}` | {m.lines} | {m.functions} | {m.average_cc:.2f} | "
                     f"{m.worst_name} ({m.worst_cc}) | {m.mi:.1f}{flag} | {mi_rank(m.mi)} |")
    return [*lines, ""]


def _hotspots(metrics: list[FileMetrics]) -> list[str]:
    """Refactoring candidates: complex functions and low-MI files."""
    complex_functions = [m for m in metrics if m.worst_cc > CC_FLAG]
    low_mi = [m for m in metrics if not m.mi_ok]
    lines = ["## Refactoring candidates", ""]
    if not complex_functions and not low_mi:
        return [*lines, f"None: no function above CC {CC_FLAG} and every file has MI ≥ "
                        f"{MI_TARGET:.0f}.", ""]
    lines += [f"- `{m.path}`: {m.worst_name} has CC {m.worst_cc}" for m in complex_functions]
    lines += [f"- `{m.path}`: MI {m.mi:.1f} below {MI_TARGET:.0f}" for m in low_mi]
    return [*lines, ""]


def main(argv: list[str] | None = None) -> int:
    """Measure, write the report and return 0 only if every objective passes."""
    parser = argparse.ArgumentParser(description="Generate docs/quality_report.md")
    parser.add_argument("--tests", action="store_true", help="also run pytest (QO7)")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    metrics = [measure(path) for path in doc_coverage.source_files()]
    tests = run_tests() if args.tests else None
    results, doc_total = doc_coverage.run()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tooling = [measure(path) for path in doc_coverage.tooling_files()]
    REPORT_PATH.write_text(render(metrics, tooling, tests) + "\n", encoding="utf-8")
    doc_coverage.write_section(doc_coverage.render(results))
    avg_cc = overall_cc(metrics)
    min_mi = min(m.mi for m in metrics)
    print(f"Average CC {avg_cc:.2f} (grade {cc_rank(round(avg_cc))}) · min MI {min_mi:.1f} · "
          f"doc coverage {'100%' if doc_coverage.passes(doc_total) else 'below 100%'}"
          + (f" · tests: {tests}" if tests else ""))
    print(f"Report written to {REPORT_PATH}")
    ok = avg_cc <= CC_TARGET and min_mi >= MI_TARGET and doc_coverage.passes(doc_total)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
