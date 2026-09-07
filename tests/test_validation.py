import decimal
from decimal import Decimal
from typing import Annotated, Any

import pytest

from symfields import S, SymFields


def round_to_2(x: Any) -> Decimal:
    return Decimal(x).quantize(Decimal("0.01"))


def test_init_formats_values():
    class Currency(SymFields):
        EUR: Annotated[Decimal, round_to_2] = S
        USD: Annotated[Decimal, round_to_2] = S("EUR") * Decimal("1.2")

    c = Currency(EUR=Decimal(123))
    assert c.__dict__ == {
        "_values": {"EUR": Decimal("123.00"), "USD": Decimal("147.60")},
        "_supplied": frozenset({"EUR"}),
    }
    assert isinstance(c.EUR, Decimal)
    assert isinstance(c.USD, Decimal)


def test_repr_shows_formatted():
    class Currency(SymFields):
        EUR: Annotated[Decimal, round_to_2] = S
        USD: Annotated[Decimal, round_to_2] = S("EUR") * Decimal("1.2")

    assert (
        repr(Currency(EUR=Decimal(123)))
        == "Currency(EUR=Decimal('123.00'), USD=Decimal('147.60'))"
    )


def test_formatter_applied_on_update():
    class Currency(SymFields):
        EUR: Annotated[Decimal, round_to_2] = S
        USD: Annotated[Decimal, round_to_2] = S("EUR") * Decimal("1.2")

    c = Currency(EUR=Decimal(123))
    c.EUR = Decimal(100)
    assert c.__dict__ == {
        "_values": {"EUR": Decimal("100.00"), "USD": Decimal("120.00")},
        "_supplied": frozenset({"EUR"}),
    }


def test_formatter_error_bubbles():
    class Currency(SymFields):
        EUR: Annotated[Decimal, round_to_2] = S
        USD: Annotated[Decimal, round_to_2] = S("EUR") * Decimal("1.2")

    with pytest.raises((ValueError, decimal.InvalidOperation)):
        Currency(EUR="hello world")  # type: ignore


def test_update_formatter_error_rolls_back():
    class Currency(SymFields):
        EUR: Annotated[Decimal, round_to_2] = S
        USD: Annotated[Decimal, round_to_2] = S("EUR") * Decimal("1.2")

    c = Currency(EUR=Decimal(123))
    pre = c.__dict__.copy()
    with pytest.raises((ValueError, decimal.InvalidOperation)):
        c.EUR = "hello world"  # type: ignore
    assert c.__dict__ == pre


def test_rounded_values_need_not_satisfy_equations():
    class Currency(SymFields):
        EUR: Annotated[Decimal, round_to_2] = S
        USD: Annotated[Decimal, round_to_2] = S("EUR") * Decimal("1.2")

    c = Currency(EUR=Decimal("123.456"))
    assert c.USD == Decimal("148.15")
    assert c.USD != c.EUR * Decimal("1.2")
