"""Unit tests for application layer use cases."""

import pytest

from ai_ready_repo.application import confirm_order, place_order, ship_order
from ai_ready_repo.domain import OrderStatus


def test_place_order_returns_pending_order() -> None:
    order = place_order("cust-1", ["widget-a"])
    assert order.customer_id == "cust-1"
    assert order.items == ["widget-a"]
    assert order.status == OrderStatus.PENDING


def test_confirm_order_transitions_to_confirmed() -> None:
    order = place_order("cust-1", ["widget-a"])
    confirm_order(order)
    assert order.status == OrderStatus.CONFIRMED


def test_ship_order_transitions_to_shipped() -> None:
    order = place_order("cust-1", ["widget-a"])
    confirm_order(order)
    ship_order(order)
    assert order.status == OrderStatus.SHIPPED


def test_ship_order_without_confirm_raises() -> None:
    order = place_order("cust-1", ["widget-a"])
    with pytest.raises(ValueError, match="Cannot transition"):
        ship_order(order)
