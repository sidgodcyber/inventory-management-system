"""Human-readable one-line summaries of activity-log payloads.

Layer: ui/views (presentation helper)
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from typing import Any


def summarize(details: dict[str, Any]) -> str:
    """One-line summary of an activity payload for the log table.

    Args:
        details: Decoded ``details_json`` of an activity entry.

    Returns:
        ``field: old → new`` for updates, quantity changes for stock movements,
        ``[context] Type: message`` for errors, ``key=value`` pairs otherwise.
    """
    if "changes" in details:
        return "; ".join(f"{key}: {_short(change.get('old'))} → {_short(change.get('new'))}"
                         for key, change in details["changes"].items())
    if "quantity_on_hand" in details:
        qty = details["quantity_on_hand"]
        return (f"{details.get('sku', '')} qty {details.get('quantity')}: "
                f"{qty.get('old')} → {qty.get('new')}  {details.get('note', '')}").strip()
    if {"old", "new"} <= details.keys() and not isinstance(details["new"], dict):
        return f"{_short(details['old'])} → {_short(details['new'])}"
    if "message" in details:
        return f"[{details.get('context', '')}] {details.get('type', '')}: {details['message']}"
    return ", ".join(f"{key}={_short(value)}" for key, value in details.items())


def _short(value: Any) -> str:
    """Compact text for a value inside a summary."""
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {v}" for k, v in value.items()) + "}"
    return str(value)
