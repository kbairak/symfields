"""Test suite for SymFields .update() method, __setattr__, and replace()."""

from decimal import Decimal

import pytest

from symfields import S, SymFields, replace


class TestUpdateBasicForwardPropagation:
    """Test basic forward propagation when updating fields."""

    def test_sum_forward_propagation(self) -> None:
        """Test updating a field propagates forward to calculated fields."""

        class Sum(SymFields):
            a: int = S
            b: int = S
            c: int = S("a") + S("b")

        sum_ = Sum(a=1, b=2)
        assert sum_.c == 3

        sum_.update(b=3)
        assert sum_.a == 1
        assert sum_.b == 3
        assert sum_.c == 4  # c updated via forward rule

    def test_multiple_forward_propagation(self) -> None:
        """Test updating propagates through multiple dependent fields."""

        class Chain(SymFields):
            a: int = S
            b: int = S("a") * 2
            c: int = S("b") + 10

        chain = Chain(a=5)
        assert chain.b == 10
        assert chain.c == 20

        chain.update(a=10)
        assert chain.a == 10
        assert chain.b == 20
        assert chain.c == 30


class TestUpdateBackwardPropagation:
    """Test backward propagation (rule inversion) when updating fields."""

    def test_chain_backward_propagation(self) -> None:
        """Test updating a derived field inverts to update independent field."""

        class Chain(SymFields):
            a: int = S
            b: int = S("a") + 1
            c: int = S("b") + 1

        chain = Chain(a=1)
        assert chain == Chain(a=1, b=2, c=3)

        # Update b - should invert to solve for a, then propagate to c
        chain.update(b=3)
        assert chain.a == 2  # Inverted from b = a + 1
        assert chain.b == 3
        assert chain.c == 4  # Forward from b

    def test_temperature_conversion_backward(self) -> None:
        """Test updating either temperature field updates the other."""

        class Temperature(SymFields):
            celsius: float = S
            fahrenheit: float = S("celsius") * 9 / 5 + 32

        temp = Temperature(celsius=0.0)
        assert temp.fahrenheit == 32.0

        temp.update(fahrenheit=212.0)
        assert temp.celsius == 100.0
        assert temp.fahrenheit == 212.0

        temp.update(celsius=0.0)
        assert temp.celsius == 0.0
        assert temp.fahrenheit == 32.0


class TestUpdateNoChange:
    """Test cases where update results in same values (no actual change)."""

    def test_sum_backward_no_change(self) -> None:
        """Test that inverting a rule with same result doesn't change other fields."""

        class Sum(SymFields):
            a: int = S
            b: int = S
            c: int = S("a") + S("b")

        sum_ = Sum(a=1, b=2, c=3)

        # Update b=3, c will become 4
        # If we try to invert c = a + b to solve for a: a = 4 - 3 = 1 (same!)
        sum_.update(b=3)
        assert sum_.a == 1  # Should not change
        assert sum_.b == 3
        assert sum_.c == 4


class TestUpdateMultipleFields:
    """Test updating multiple fields at once."""

    def test_update_two_fields(self) -> None:
        """Test updating two independent fields."""

        class Sum(SymFields):
            a: int = S
            b: int = S
            c: int = S("a") + S("b")

        sum_ = Sum(a=1, b=2, c=3)
        sum_.update(a=5, b=10)
        assert sum_.a == 5
        assert sum_.b == 10
        assert sum_.c == 15

    def test_update_independent_and_derived(self) -> None:
        """Test updating both independent and derived fields together."""

        class Calc(SymFields):
            a: int = S
            b: int = S("a") * 2

        calc = Calc(a=5)
        assert calc.b == 10

        # Update both a and b - b should take its new value
        # Then validation should check if b == a * 2
        # This would fail validation if they're inconsistent
        calc.update(a=10, b=20)
        assert calc.a == 10
        assert calc.b == 20


class TestUpdateValidation:
    """Test validation after updates."""

    def test_validation_error_on_inconsistent_update(self) -> None:
        """Test that inconsistent updates raise validation errors."""

        class Sum(SymFields):
            a: int = S
            b: int = S
            c: int = S("a") + S("b")

        sum_ = Sum(a=1, b=2, c=3)

        # Try to update to inconsistent state
        with pytest.raises(ValueError, match="Validation failed"):
            sum_.update(a=10, b=10, c=5)  # 10 + 10 != 5


class TestUpdateWithLambdas:
    """Test update with lambda/callable fields."""

    def test_lambda_field_updates_with_dependencies(self) -> None:
        """Test that lambda fields update when their dependencies change."""

        class Rectangle(SymFields):
            width: int = S
            height: int = S
            area: int = S("width") * S("height")
            label: str = S(lambda width, height: f"{width}x{height}")

        rect = Rectangle(width=5, height=3)
        assert rect.area == 15
        assert rect.label == "5x3"

        rect.update(width=10)
        assert rect.width == 10
        assert rect.height == 3
        assert rect.area == 30
        assert rect.label == "10x3"


class TestUpdateWithDecimalPrecision:
    """Test update with Annotated cast functions."""

    def test_update_maintains_precision(self) -> None:
        """Test that updates maintain decimal precision from Annotated."""
        from decimal import ROUND_HALF_UP
        from typing import Annotated, Any

        def cast_2_places(value: Any) -> Decimal:
            return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        class Price(SymFields):
            subtotal: Decimal = S
            tax_rate: Decimal = S
            total: Annotated[Decimal, cast_2_places] = S("subtotal") * (1 + S("tax_rate"))

        price = Price(subtotal=Decimal("10.00"), tax_rate=Decimal("0.23"))
        assert price.total == Decimal("12.30")

        price.update(subtotal=Decimal("20.00"))
        assert price.subtotal == Decimal("20.00")
        assert price.total == Decimal("24.60")  # Still 2 decimal places


class TestUpdateErrorCases:
    """Test error cases and edge cases for update."""

    def test_cannot_update_ambiguous_fields(self) -> None:
        """Test that updating fields with multiple solutions raises error."""

        class Rectangle(SymFields):
            width: float = S
            height: float = S
            area: float = S("width") * S("height")

        rect = Rectangle(width=5.0, height=3.0)
        assert rect.area == 15.0

        # Updating area alone is ambiguous - should width change? height? both?
        # Can't determine which field to update
        with pytest.raises(ValueError, match=r"Cannot determine|ambiguous|under-constrained"):
            rect.update(area=30.0)

    def test_update_independent_field_propagates_forward(self) -> None:
        """Test that updating an independent field propagates forward correctly."""

        class Rectangle(SymFields):
            width: float = S
            height: float = S
            area: float = S("width") * S("height")

        rect = Rectangle(width=5.0, height=3.0)

        # Updating width propagates to area (height stays unchanged)
        rect.update(width=10.0)
        assert rect.width == 10.0
        assert rect.height == 3.0  # Unchanged
        assert rect.area == 30.0  # Propagated forward

    def test_update_nonexistent_field(self) -> None:
        """Test updating a field that doesn't exist raises error."""

        class Sum(SymFields):
            a: int = S
            b: int = S
            c: int = S("a") + S("b")

        sum_ = Sum(a=1, b=2)

        with pytest.raises((ValueError, AttributeError, TypeError)):
            sum_.update(nonexistent=10)


class TestUpdateComplexScenarios:
    """Test complex update scenarios with multiple rules."""

    def test_circle_update_from_any_field(self) -> None:
        """Test updating a hub-and-spoke dependency graph."""
        import math

        class Circle(SymFields):
            radius: float = S
            diameter: float = S("radius") * 2
            circumference: float = S("radius") * 2 * math.pi

        circle = Circle(radius=5.0)
        assert circle.diameter == 10.0
        assert abs(circle.circumference - 31.41592653589793) < 0.0001

        # Update radius - both dependent fields should update
        circle.update(radius=10.0)
        assert circle.radius == 10.0
        assert circle.diameter == 20.0
        assert abs(circle.circumference - 62.83185307179586) < 0.0001

        # Update diameter - should invert to radius, then update circumference
        circle.update(diameter=30.0)
        assert circle.radius == 15.0
        assert circle.diameter == 30.0
        assert abs(circle.circumference - 94.24777960769379) < 0.0001

    def test_multi_round_propagation(self) -> None:
        """Test that propagation continues for multiple rounds."""

        class LongChain(SymFields):
            a: int = S
            b: int = S("a") + 1
            c: int = S("b") + 1
            d: int = S("c") + 1

        chain = LongChain(a=1)
        assert chain.b == 2
        assert chain.c == 3
        assert chain.d == 4

        # Update c - should invert to b, then to a, then forward to d
        chain.update(c=10)
        assert chain.a == 8  # Inverted: c=10 -> b=9 -> a=8
        assert chain.b == 9
        assert chain.c == 10
        assert chain.d == 11  # Forward from c


class TestSetattr:
    """Test __setattr__ integration with constraint propagation."""

    def test_setattr_forward_propagation(self) -> None:
        """Test that setting a field via attribute assignment propagates forward."""

        class Sum(SymFields):
            a: int = S
            b: int = S
            c: int = S("a") + S("b")

        sum_ = Sum(a=1, b=2)
        assert sum_.c == 3

        # Set via attribute assignment
        sum_.b = 3
        assert sum_.a == 1
        assert sum_.b == 3
        assert sum_.c == 4  # Propagated

    def test_setattr_backward_propagation(self) -> None:
        """Test that setting a derived field inverts equations."""

        class Temperature(SymFields):
            celsius: float = S
            fahrenheit: float = S("celsius") * 9 / 5 + 32

        temp = Temperature(celsius=0.0)
        assert temp.fahrenheit == 32.0

        # Set derived field - should invert
        temp.fahrenheit = 212.0
        assert temp.celsius == 100.0
        assert temp.fahrenheit == 212.0

    def test_setattr_multi_round_propagation(self) -> None:
        """Test that attribute assignment propagates through chains."""

        class Chain(SymFields):
            a: int = S
            b: int = S("a") + 1
            c: int = S("b") + 1

        chain = Chain(a=1)
        assert chain == Chain(a=1, b=2, c=3)

        # Set b - should invert to a and forward to c
        chain.b = 5
        assert chain.a == 4
        assert chain.b == 5
        assert chain.c == 6

    def test_setattr_equivalent_to_update(self) -> None:
        """Test that setattr behaves identically to .update()."""

        class Rectangle(SymFields):
            width: float = S
            height: float = S
            area: float = S("width") * S("height")

        rect1 = Rectangle(width=5.0, height=3.0)
        rect2 = Rectangle(width=5.0, height=3.0)

        # One via setattr, one via update
        rect1.width = 10.0
        rect2.update(width=10.0)

        assert rect1.width == rect2.width
        assert rect1.height == rect2.height
        assert rect1.area == rect2.area

    def test_setattr_with_lambdas(self) -> None:
        """Test that setattr works with lambda fields."""

        class Rectangle(SymFields):
            width: int = S
            height: int = S
            area: int = S("width") * S("height")
            label: str = S(lambda width, height: f"{width}x{height}")

        rect = Rectangle(width=5, height=3)
        assert rect.label == "5x3"

        rect.width = 10
        assert rect.label == "10x3"

    def test_setattr_validation_error(self) -> None:
        """Test that setattr raises validation errors for inconsistent state."""

        class Rectangle(SymFields):
            width: float = S
            height: float = S
            area: float = S("width") * S("height")

        rect = Rectangle(width=5.0, height=3.0)

        # Setting area is ambiguous
        with pytest.raises(ValueError, match=r"Cannot determine|ambiguous|under-constrained"):
            rect.area = 30.0


class TestReplace:
    """Test replace() function for immutable-style updates."""

    def test_replace_basic(self) -> None:
        """Test basic replace functionality."""

        class Sum(SymFields):
            a: int = S
            b: int = S
            c: int = S("a") + S("b")

        original = Sum(a=1, b=2)
        assert original.c == 3

        # Replace returns new instance
        new = replace(original, b=3)

        # Original unchanged
        assert original.a == 1
        assert original.b == 2
        assert original.c == 3

        # New has updated values
        assert new.a == 1
        assert new.b == 3
        assert new.c == 4

    def test_replace_forward_propagation(self) -> None:
        """Test that replace propagates changes forward."""

        class Circle(SymFields):
            radius: float = S
            diameter: float = S("radius") * 2

        original = Circle(radius=5.0)
        new = replace(original, radius=10.0)

        assert original.radius == 5.0
        assert original.diameter == 10.0

        assert new.radius == 10.0
        assert new.diameter == 20.0

    def test_replace_backward_propagation(self) -> None:
        """Test that replace can invert equations."""

        class Temperature(SymFields):
            celsius: float = S
            fahrenheit: float = S("celsius") * 9 / 5 + 32

        original = Temperature(celsius=0.0)
        new = replace(original, fahrenheit=212.0)

        assert original.celsius == 0.0
        assert original.fahrenheit == 32.0

        assert new.celsius == 100.0
        assert new.fahrenheit == 212.0

    def test_replace_multiple_fields(self) -> None:
        """Test replacing multiple fields at once."""

        class Sum(SymFields):
            a: int = S
            b: int = S
            c: int = S("a") + S("b")

        original = Sum(a=1, b=2, c=3)
        new = replace(original, a=5, b=10)

        assert original.a == 1
        assert original.b == 2
        assert original.c == 3

        assert new.a == 5
        assert new.b == 10
        assert new.c == 15

    def test_replace_preserves_type(self) -> None:
        """Test that replace returns the same type."""

        class MyClass(SymFields):
            a: int = S
            b: int = S("a") * 2

        original = MyClass(a=5)
        new = replace(original, a=10)

        assert isinstance(new, MyClass)
        assert type(new) is type(original)

    def test_replace_with_annotated(self) -> None:
        """Test that replace maintains Annotated precision."""
        from decimal import ROUND_HALF_UP
        from typing import Annotated, Any

        def cast_2_places(value: Any) -> Decimal:
            return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        class Price(SymFields):
            subtotal: Decimal = S
            total: Annotated[Decimal, cast_2_places] = S("subtotal") * Decimal("1.23")

        original = Price(subtotal=Decimal("10.00"))
        new = replace(original, subtotal=Decimal("20.00"))

        assert original.total == Decimal("12.30")
        assert new.total == Decimal("24.60")

    def test_replace_no_fields_returns_different_instance(self) -> None:
        """Test that replace with no changes creates a new instance."""

        class Sum(SymFields):
            a: int = S
            b: int = S
            c: int = S("a") + S("b")

        original = Sum(a=1, b=2)
        new = replace(original)

        # Different instances
        assert original is not new

        # Same values
        assert new.a == original.a
        assert new.b == original.b
        assert new.c == original.c

    def test_replace_validation_error(self) -> None:
        """Test that replace raises validation errors."""

        class Rectangle(SymFields):
            width: float = S
            height: float = S
            area: float = S("width") * S("height")

        original = Rectangle(width=5.0, height=3.0)

        # Replacing only area is ambiguous - can't determine width/height
        # This will fail during __init__ when trying to solve the system
        with pytest.raises(ValueError, match=r"Cannot calculate all fields|Validation failed"):
            replace(original, area=30.0)
