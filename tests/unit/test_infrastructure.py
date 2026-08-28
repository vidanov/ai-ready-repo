"""Unit tests for infrastructure layer."""

from ai_ready_repo.domain import Order
from ai_ready_repo.infrastructure import InMemoryOrderRepository


def test_save_and_get_order() -> None:
    repo = InMemoryOrderRepository()
    order = Order(customer_id="cust-1", items=["widget-a"])
    repo.save(order)
    assert repo.get(order.id) is order


def test_get_missing_order_returns_none() -> None:
    repo = InMemoryOrderRepository()
    order = Order(customer_id="cust-1", items=["widget-a"])
    assert repo.get(order.id) is None


def test_all_returns_saved_orders() -> None:
    repo = InMemoryOrderRepository()
    a = Order(customer_id="cust-1", items=["widget-a"])
    b = Order(customer_id="cust-2", items=["widget-b"])
    repo.save(a)
    repo.save(b)
    result = repo.all()
    assert len(result) == 2
    assert a in result
    assert b in result


def test_save_overwrites_existing_order() -> None:
    repo = InMemoryOrderRepository()
    order = Order(customer_id="cust-1", items=["widget-a"])
    repo.save(order)
    repo.save(order)  # same id
    assert len(repo.all()) == 1
