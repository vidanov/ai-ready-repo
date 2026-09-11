"""
Integration test: full place → confirm → ship → deliver workflow.

Exercises the application layer with InMemoryOrderRepository — no mocks
of domain or application logic.
"""

from ai_ready_repo.application import confirm_order, place_order, ship_order
from ai_ready_repo.domain import OrderStatus
from ai_ready_repo.infrastructure import InMemoryOrderRepository


def test_place_confirm_ship_deliver_workflow() -> None:
    repo = InMemoryOrderRepository()

    order = place_order(customer_id="cust-42", items=["widget-a", "widget-b"])
    assert order.status == OrderStatus.PENDING
    repo.save(order)

    confirm_order(order)
    assert order.status == OrderStatus.CONFIRMED
    repo.save(order)

    ship_order(order)
    assert order.status == OrderStatus.SHIPPED
    repo.save(order)

    order.deliver()
    assert order.status == OrderStatus.DELIVERED
    repo.save(order)

    persisted = repo.get(order.id)
    assert persisted is not None
    assert persisted.status == OrderStatus.DELIVERED
    assert persisted.customer_id == "cust-42"
    assert persisted.items == ["widget-a", "widget-b"]
