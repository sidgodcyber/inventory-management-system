"""CSV export via pandas, with Excel-friendly UTF-8 encoding.

Layer: utils (stateless helpers, used by services)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# A column spec is (key in each row dict, header written to the file).
ColumnSpec = Sequence[tuple[str, str]]


def default_export_path(export_dir: Path, prefix: str) -> Path:
    """Timestamped file path such as ``exports/products_20261030_141500.csv``."""
    return export_dir / f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}.csv"


def write_csv(rows: Sequence[Mapping[str, Any]], columns: ColumnSpec, path: Path) -> Path:
    """Write ``rows`` to ``path`` with the chosen columns and headers.

    Args:
        rows: One mapping per record.
        columns: ``(key, header)`` pairs in output order.
        path: Destination file; parent folders are created.

    Returns:
        The written path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = [key for key, _ in columns]
    frame = pd.DataFrame([{key: row.get(key) for key in keys} for row in rows], columns=keys)
    frame.columns = [header for _, header in columns]
    # utf-8-sig adds a BOM so Excel shows symbols such as the rupee sign correctly.
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path
