"""
Application layer: use cases that orchestrate domain objects.

May import from domain. Must not import from infrastructure.

Example use case: place an order, advance its status, cancel it.
"""

from ai_ready_repo.domain import Order, OrderStatus


def place_order(customer_id: str, items: list[str]) -> Order:
    """Create and return a new pending order."""
    return Order(customer_id=customer_id, items=items)


def confirm_order(order: Order) -> None:
    """Confirm a pending order."""
    order.transition(OrderStatus.CONFIRMED)


def ship_order(order: Order) -> None:
    """Mark a confirmed order as shipped."""
    order.transition(OrderStatus.SHIPPED)
