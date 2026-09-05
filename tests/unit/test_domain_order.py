"""Unit tests for domain.Order aggregate."""

import pytest

from ai_ready_repo.domain import Order, OrderStatus


def test_order_creation() -> None:
    order = Order(customer_id="cust-1", items=["item-a", "item-b"])
    assert order.customer_id == "cust-1"
    assert order.items == ["item-a", "item-b"]
    assert order.status == OrderStatus.PENDING


def test_order_requires_customer_id() -> None:
    with pytest.raises(ValueError, match="customer_id is required"):
        Order(customer_id="", items=["item-a"])


def test_order_requires_at_least_one_item() -> None:
    with pytest.raises(ValueError, match="at least one item"):
        Order(customer_id="cust-1", items=[])


def test_valid_transition_pending_to_confirmed() -> None:
    order = Order(customer_id="cust-1", items=["item-a"])
    order.transition(OrderStatus.CONFIRMED)
    assert order.status == OrderStatus.CONFIRMED


def test_valid_transition_confirmed_to_shipped() -> None:
    order = Order(customer_id="cust-1", items=["item-a"])
    order.transition(OrderStatus.CONFIRMED)
    order.transition(OrderStatus.SHIPPED)
    assert order.status == OrderStatus.SHIPPED


def test_valid_transition_shipped_to_delivered() -> None:
    order = Order(customer_id="cust-1", items=["item-a"])
    order.transition(OrderStatus.CONFIRMED)
    order.transition(OrderStatus.SHIPPED)
    order.transition(OrderStatus.DELIVERED)
    assert order.status == OrderStatus.DELIVERED


def test_invalid_transition_pending_to_shipped_raises() -> None:
    order = Order(customer_id="cust-1", items=["item-a"])
    with pytest.raises(ValueError, match="Cannot transition from 'pending' to 'shipped'"):
        order.transition(OrderStatus.SHIPPED)


def test_cancel_from_pending() -> None:
    order = Order(customer_id="cust-1", items=["item-a"])
    order.cancel()
    assert order.status == OrderStatus.CANCELLED


def test_cancel_from_confirmed() -> None:
    order = Order(customer_id="cust-1", items=["item-a"])
    order.transition(OrderStatus.CONFIRMED)
    order.cancel()
    assert order.status == OrderStatus.CANCELLED


def test_cannot_cancel_delivered_order() -> None:
    order = Order(customer_id="cust-1", items=["item-a"])
    order.transition(OrderStatus.CONFIRMED)
    order.transition(OrderStatus.SHIPPED)
    order.transition(OrderStatus.DELIVERED)
    with pytest.raises(ValueError, match="Cannot transition"):
        order.cancel()


def test_is_terminal_delivered() -> None:
    order = Order(customer_id="cust-1", items=["item-a"])
    order.transition(OrderStatus.CONFIRMED)
    order.transition(OrderStatus.SHIPPED)
    order.transition(OrderStatus.DELIVERED)
    assert order.is_terminal() is True


def test_is_terminal_pending_is_false() -> None:
    order = Order(customer_id="cust-1", items=["item-a"])
    assert order.is_terminal() is False


def test_order_has_unique_id() -> None:
    a = Order(customer_id="cust-1", items=["item-a"])
    b = Order(customer_id="cust-1", items=["item-a"])
    assert a.id != b.id


def test_status_cannot_bypass_transition() -> None:
    order = Order(customer_id="cust-1", items=["item-a"])
    with pytest.raises(AttributeError):
        order.status = OrderStatus.DELIVERED  # type: ignore[misc]
    assert order.status == OrderStatus.PENDING
