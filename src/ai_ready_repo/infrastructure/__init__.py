"""
Infrastructure layer: external services, databases, APIs.

May import from domain and application.
Never imported by domain or application.

Example: in-memory order repository (replace with a real DB implementation).
"""

from uuid import UUID

from ai_ready_repo.domain import Order


class InMemoryOrderRepository:
    """Simple in-memory store — swap for a database-backed implementation."""

    def __init__(self) -> None:
        self._store: dict[UUID, Order] = {}

    def save(self, order: Order) -> None:
        self._store[order.id] = order

    def get(self, order_id: UUID) -> Order | None:
        return self._store.get(order_id)

    def all(self) -> list[Order]:
        return list(self._store.values())
