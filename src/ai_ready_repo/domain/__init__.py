"""
Domain layer: pure business logic, no framework or infrastructure imports.

This module demonstrates a simple entity with a state machine and domain rules.
Replace with your actual domain model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4


class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# Valid transitions: maps current status to allowed next statuses.
_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING: frozenset({OrderStatus.CONFIRMED, OrderStatus.CANCELLED}),
    OrderStatus.CONFIRMED: frozenset({OrderStatus.SHIPPED, OrderStatus.CANCELLED}),
    OrderStatus.SHIPPED: frozenset({OrderStatus.DELIVERED}),
    OrderStatus.DELIVERED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


@dataclass
class Order:
    """
    Order aggregate root.

    Enforces valid status transitions and requires at least one item.
    Status changes go through transition(), never by direct assignment.
    """

    id: UUID = field(default_factory=uuid4)
    customer_id: str = ""
    items: list[str] = field(default_factory=list)
    _status: OrderStatus = field(default=OrderStatus.PENDING, init=False, repr=False)

    @property
    def status(self) -> OrderStatus:
        """Read the current state; use transition() to change it."""
        return self._status

    def __post_init__(self) -> None:
        if not self.customer_id:
            raise ValueError("customer_id is required")
        if not self.items:
            raise ValueError("Order must contain at least one item")

    def transition(self, new_status: OrderStatus) -> None:
        """Move to new_status if the transition is valid."""
        allowed = _TRANSITIONS[self.status]
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition from {self.status.value!r} to {new_status.value!r}. "
                f"Allowed: {[s.value for s in allowed] or 'none'}"
            )
        self._status = new_status

    def cancel(self) -> None:
        """Convenience method — cancels if allowed."""
        self.transition(OrderStatus.CANCELLED)

    def is_terminal(self) -> bool:
        """Returns True if the order cannot change status further."""
        return not _TRANSITIONS[self.status]
