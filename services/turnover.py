"""Pure pandas calculations for inventory turnover and movement charts.

No database access happens here. :class:`services.report_service.ReportService`
fetches the inputs from repositories and passes them in, which keeps the maths
easy to read and to unit-test with hand-made data.

Formulas:

* ``COGS``           = sum of OUT quantity x unit cost in the period
* ``closing qty(d)`` = stock at the end of day d, rebuilt backwards from today
* ``avg inventory``  = mean of closing qty(d) over the period x unit cost
* ``turnover``       = COGS / average inventory value
* ``days of stock``  = on hand / (units issued / days in period)

Layer: services
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

import pandas as pd

from models.product import Product
from models.reports import TurnoverRow


def average_daily_quantity(on_hand: pd.Series, deltas: Sequence[tuple[int, str, int]],
                           after_end: dict[int, int], days: list[date]) -> pd.Series:
    """Mean end-of-day stock per product across ``days``.

    Args:
        on_hand: Current quantity indexed by product id.
        deltas: ``(product_id, YYYY-MM-DD, signed change)`` inside the period.
        after_end: Signed change per product *after* the period (undone first).
        days: Every calendar day of the period, in order.

    Returns:
        Average quantity indexed by product id.
    """
    closing_at_end = on_hand - on_hand.index.map(lambda i: after_end.get(i, 0))
    frame = pd.DataFrame(list(deltas), columns=["product_id", "day", "delta"])
    table = frame.pivot_table(index="product_id", columns="day", values="delta",
                              aggfunc="sum", fill_value=0)
    table.columns = pd.to_datetime(table.columns).date
    table = table.reindex(index=on_hand.index, columns=days, fill_value=0)
    # closing(d) = closing at period end minus every movement later than day d.
    later = table.sum(axis=1).to_numpy()[:, None] - table.cumsum(axis=1).to_numpy()
    daily_closing = closing_at_end.to_numpy()[:, None] - later
    return pd.Series(daily_closing.mean(axis=1), index=on_hand.index)


def turnover_table(products: Sequence[Product], issues: dict[int, tuple[int, float]],
                   average_qty: pd.Series, period_days: int) -> pd.DataFrame:
    """Per-product turnover, usage and days of stock.

    Args:
        products: Active products.
        issues: ``{product_id: (units issued, COGS)}`` for the period.
        average_qty: Average daily quantity per product id.
        period_days: Number of days in the period.

    Returns:
        One row per product (columns match :class:`~models.reports.TurnoverRow`).
    """
    frame = pd.DataFrame([_product_record(p) for p in products])
    ids = frame["product_id"]
    frame["units_sold"] = ids.map(lambda i: issues.get(i, (0, 0.0))[0])
    frame["cogs"] = ids.map(lambda i: issues.get(i, (0, 0.0))[1])
    frame["average_inventory_value"] = ids.map(average_qty) * frame["unit_cost"]
    average = frame["average_inventory_value"]
    frame["turnover"] = (frame["cogs"] / average.where(average > 0)).fillna(0.0)
    frame["avg_daily_usage"] = frame["units_sold"] / period_days
    usage = frame["avg_daily_usage"]
    frame["days_of_stock"] = frame["quantity_on_hand"] / usage.where(usage > 0)
    return frame.drop(columns=["unit_cost"])


def to_rows(frame: pd.DataFrame) -> list[TurnoverRow]:
    """Convert a turnover table to report rows, highest turnover first.

    Args:
        frame: Output of :func:`turnover_table`.

    Returns:
        Rounded :class:`~models.reports.TurnoverRow` objects.
    """
    if frame.empty:
        return []
    ordered = frame.sort_values(["turnover", "cogs"], ascending=False)
    return [TurnoverRow(**_clean_row(row)) for row in ordered.to_dict("records")]


def overall_turnover(frame: pd.DataFrame) -> float:
    """Store-wide turnover: total COGS / total average inventory value.

    Args:
        frame: Output of :func:`turnover_table` (may be empty).

    Returns:
        The ratio rounded to 2 decimals (``0.0`` when there is no inventory).
    """
    average = frame["average_inventory_value"].sum() if not frame.empty else 0.0
    return round(float(frame["cogs"].sum() / average), 2) if average > 0 else 0.0


def daily_movement_table(totals: Sequence[tuple[str, str, int]], days: list[date],
                         types: list[str]) -> pd.DataFrame:
    """Units per day and movement type with missing days filled with zero.

    Args:
        totals: ``(YYYY-MM-DD, type, units)`` rows.
        days: Every day of the chart window.
        types: Movement types to keep as columns, in order.

    Returns:
        Integer DataFrame indexed by date with one column per type.
    """
    frame = pd.DataFrame(list(totals), columns=["day", "type", "units"])
    table = frame.pivot_table(index="day", columns="type", values="units",
                              aggfunc="sum", fill_value=0)
    table.index = pd.to_datetime(table.index).date
    return table.reindex(index=days, columns=types, fill_value=0).astype(int)


def _product_record(product: Product) -> dict[str, Any]:
    """The product columns the turnover table starts from."""
    return {"product_id": product.id, "sku": product.sku, "name": product.name,
            "category_name": product.category_name,
            "quantity_on_hand": product.quantity_on_hand, "unit_cost": product.unit_cost}


def _clean_row(row: dict[str, Any]) -> dict[str, Any]:
    """Round money/ratios and turn NaN days-of-stock into ``None``."""
    days = row["days_of_stock"]
    return {
        **row,
        "product_id": int(row["product_id"]),
        "quantity_on_hand": int(row["quantity_on_hand"]),
        "units_sold": int(row["units_sold"]),
        "cogs": round(float(row["cogs"]), 2),
        "average_inventory_value": round(float(row["average_inventory_value"]), 2),
        "turnover": round(float(row["turnover"]), 2),
        "avg_daily_usage": round(float(row["avg_daily_usage"]), 2),
        "days_of_stock": None if pd.isna(days) else round(float(days), 1),
    }
