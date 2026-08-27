"""Unit tests for domain.Money value object."""

from decimal import Decimal

import pytest

from ai_ready_repo.domain import Money


def test_money_creation() -> None:
    m = Money(Decimal("10.00"), "EUR")
    assert m.amount == Decimal("10.00")
    assert m.currency == "EUR"


def test_money_add_same_currency() -> None:
    a = Money(Decimal("10.00"), "EUR")
    b = Money(Decimal("5.50"), "EUR")
    result = a.add(b)
    assert result.amount == Decimal("15.50")
    assert result.currency == "EUR"


def test_money_add_different_currency_raises() -> None:
    a = Money(Decimal("10.00"), "EUR")
    b = Money(Decimal("10.00"), "USD")
    with pytest.raises(ValueError, match="Cannot add EUR and USD"):
        a.add(b)


def test_money_negative_amount_raises() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        Money(Decimal("-1.00"), "EUR")


def test_money_invalid_currency_raises() -> None:
    with pytest.raises(ValueError, match="3-letter ISO code"):
        Money(Decimal("1.00"), "EURO")


def test_money_is_immutable() -> None:
    m = Money(Decimal("10.00"), "EUR")
    with pytest.raises(AttributeError):
        m.amount = Decimal("99.00")  # type: ignore[misc]


def test_money_str() -> None:
    m = Money(Decimal("10.5"), "EUR")
    assert str(m) == "10.50 EUR"
