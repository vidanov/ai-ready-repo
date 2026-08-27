"""
Domain layer: pure business logic, no framework or infrastructure imports.

This module demonstrates a simple value object and domain rule.
Replace with your actual domain model.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    """
    Monetary value object.

    Uses Decimal to avoid floating-point errors.
    Never use float for monetary values.
    """

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if self.amount < Decimal("0"):
            raise ValueError(f"Amount cannot be negative: {self.amount}")
        if not self.currency or len(self.currency) != 3:
            raise ValueError(f"Currency must be a 3-letter ISO code: {self.currency!r}")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"
