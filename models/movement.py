"""Result of a stock movement: the stored transaction and the updated product.

Layer: models
Author: Siddhi Baluja (240302054)
"""

from __future__ import annotations

from dataclasses import dataclass

from models.product import Product
from models.stock_transaction import StockTransaction


@dataclass
class MovementResult:
    """Outcome of a stock movement.

    Attributes:
        transaction: The stored movement.
        product: The product after the movement.
    """

    transaction: StockTransaction
    product: Product

    @property
    def low_stock_alert(self) -> bool:
        """True when the movement left the product at or below reorder level."""
        return self.product.is_low_stock
