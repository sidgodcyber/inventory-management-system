"""Read-only report models produced by the analytics service.

Layer: models
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TurnoverRow:
    """Inventory turnover figures for one product over a period.

    Attributes:
        product_id: Product primary key.
        sku: Product SKU.
        name: Product name.
        category_name: Category name.
        quantity_on_hand: Current stock.
        units_sold: Units issued (OUT) in the period.
        cogs: Cost of goods sold: sum of OUT quantity x unit cost.
        average_inventory_value: (opening value + closing value) / 2.
        turnover: COGS / average inventory value (``0`` when no inventory).
        avg_daily_usage: Units sold / days in period.
        days_of_stock: Days until stockout at current usage (``None`` = no usage).
    """

    product_id: int
    sku: str
    name: str
    category_name: str
    quantity_on_hand: int
    units_sold: int
    cogs: float
    average_inventory_value: float
    turnover: float
    avg_daily_usage: float
    days_of_stock: float | None


@dataclass
class DashboardStats:
    """Headline numbers for the dashboard stat cards.

    Attributes:
        total_products: Active products.
        total_stock_value: Sum of quantity x unit cost.
        low_stock_count: Products at or below reorder level (incl. stockouts).
        stockout_count: Products with zero stock.
        turnover: Overall inventory turnover for the period.
        period_days: Length of the turnover period.
    """

    total_products: int
    total_stock_value: float
    low_stock_count: int
    stockout_count: int
    turnover: float
    period_days: int
