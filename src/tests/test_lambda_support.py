"""Test suite for lambda/callable support in SymFields."""

import math
from decimal import Decimal

import pytest

from symfields import S, SymFields

# Type checkers can't understand that lambdas are processed at class definition time
# mypy: disable-error-code="assignment"


class TestBasicLambdaFunctionality:
    """Test basic lambda functionality."""

    def test_simple_lambda_forward(self) -> None:
        """Test simple lambda calculation."""

        class Rectangle(SymFields):
            width: float = S
            height: float = S
            area: float = lambda width, height: width * height

        r = Rectangle(width=5, height=4)
        assert r.width == 5
        assert r.height == 4
        assert r.area == 20

    def test_lambda_with_one_parameter(self) -> None:
        """Test lambda with single parameter."""

        class Square(SymFields):
            side: float = S
            area: float = lambda side: side ** 2

        s = Square(side=5)
        assert s.side == 5
        assert s.area == 25

    def test_lambda_with_no_parameters(self) -> None:
        """Test lambda with no parameters (default factory)."""

        class WithDefault(SymFields):
            value: float = S
            random_id: int = lambda: 42

        w = WithDefault(value=10)
        assert w.value == 10
        assert w.random_id == 42

    def test_lambda_cannot_solve_backward(self) -> None:
        """Test that lambdas are forward-only, cannot be inverted."""

        class Rectangle(SymFields):
            width: float = S
            height: float = S
            area: float = lambda width, height: width * height

        # Cannot solve for width given area and height
        with pytest.raises(ValueError, match="Cannot calculate all fields"):
            Rectangle(area=20, height=4)


class TestLambdaNonNumericTypes:
    """Test lambdas with non-numeric types."""

    def test_lambda_returning_string(self) -> None:
        """Test lambda that returns a string."""

        class Person(SymFields):
            first_name: str = S
            last_name: str = S
            full_name: str = lambda first_name, last_name: f"{first_name} {last_name}"

        p = Person(first_name="John", last_name="Doe")
        assert p.first_name == "John"
        assert p.last_name == "Doe"
        assert p.full_name == "John Doe"

    def test_lambda_returning_bool(self) -> None:
        """Test lambda that returns a boolean."""

        class AgeCheck(SymFields):
            age: int = S
            is_adult: bool = lambda age: age >= 18

        a1 = AgeCheck(age=20)
        assert a1.is_adult is True

        a2 = AgeCheck(age=15)
        assert a2.is_adult is False

    def test_lambda_with_decimal(self) -> None:
        """Test lambda with Decimal type."""

        class Money(SymFields):
            price: Decimal = S
            quantity: Decimal = S
            total: Decimal = lambda price, quantity: price * quantity

        m = Money(price=Decimal("10.50"), quantity=Decimal("3"))
        assert m.total == Decimal("31.50")


class TestMixedSympyAndLambda:
    """Test classes with both sympy expressions and lambdas."""

    def test_mixed_rules(self) -> None:
        """Test class with both sympy and lambda rules."""

        class Mixed(SymFields):
            width: float = S
            height: float = S
            area: float = S("width") * S("height")  # Sympy - invertible
            label: str = lambda width, height: f"{width}x{height}"  # Lambda - forward only

        # Can solve for width using sympy expression
        m1 = Mixed(area=20, height=4)
        assert m1.width == 5
        assert m1.label == "5.0x4"

        # Can calculate both area and label forward
        m2 = Mixed(width=5, height=4)
        assert m2.area == 20
        assert m2.label == "5x4"

    def test_lambda_depends_on_sympy_calculated_field(self) -> None:
        """Test lambda that depends on a field calculated by sympy."""

        class Calculated(SymFields):
            a: float = S
            b: float = S
            sum_ab: float = S("a") + S("b")  # Sympy
            message: str = lambda sum_ab: f"Sum is {sum_ab}"  # Lambda uses sympy result

        c = Calculated(a=10, b=20)
        assert c.sum_ab == 30
        assert c.message == "Sum is 30.0"


class TestLambdaValidation:
    """Test validation of lambda signatures."""

    def test_lambda_parameter_must_match_field(self) -> None:
        """Test that lambda parameters must match existing fields."""

        with pytest.raises(TypeError, match="parameter 'unknown' is not a defined field"):

            class Invalid(SymFields):
                width: float = S
                area: float = lambda width, unknown: width * unknown

    def test_lambda_no_default_arguments(self) -> None:
        """Test that lambda parameters cannot have defaults."""

        with pytest.raises(TypeError, match="cannot have default value"):

            class Invalid(SymFields):
                width: float = S
                area: float = lambda width, height=10: width * height

    def test_lambda_no_var_args(self) -> None:
        """Test that lambdas cannot use *args."""

        with pytest.raises(TypeError, match="cannot use \\*args"):

            class Invalid(SymFields):
                values: list = S
                result: float = lambda *values: sum(values)

    def test_lambda_no_var_kwargs(self) -> None:
        """Test that lambdas cannot use **kwargs."""

        with pytest.raises(TypeError, match=r"cannot use.*\*\*kwargs"):

            class Invalid(SymFields):
                data: dict = S
                result: str = lambda **data: str(data)


class TestLambdaWithExternalFunctions:
    """Test lambdas that call external functions."""

    def test_lambda_with_math_functions(self) -> None:
        """Test lambda using math module functions."""

        class Circle(SymFields):
            radius: float = S
            area: float = lambda radius: math.pi * radius ** 2

        c = Circle(radius=5)
        assert math.isclose(c.area, math.pi * 25)

    def test_regular_function_not_just_lambda(self) -> None:
        """Test that regular functions work, not just lambdas."""

        def calculate_bmi(weight: float, height: float) -> float:
            return weight / (height ** 2)

        class Person(SymFields):
            weight: float = S
            height: float = S
            bmi: float = calculate_bmi

        p = Person(weight=70, height=1.75)
        expected_bmi = 70 / (1.75 ** 2)
        assert math.isclose(p.bmi, expected_bmi)


class TestLambdaValidationErrors:
    """Test validation error messages with lambdas."""

    def test_validation_error_shows_callable_signature(self) -> None:
        """Test that validation errors show lambda signature."""

        class Rectangle(SymFields):
            width: float = S
            height: float = S
            area: float = lambda width, height: width * height

        with pytest.raises(ValueError, match=r"<callable\(width, height\)>"):
            Rectangle(width=5, height=4, area=25)  # Wrong area

    def test_validation_error_with_string_no_difference(self) -> None:
        """Test validation error for non-numeric types doesn't show difference."""

        class Person(SymFields):
            first_name: str = S
            last_name: str = S
            full_name: str = lambda first_name, last_name: f"{first_name} {last_name}"

        # Should raise error but not try to show "Difference" for strings
        with pytest.raises(ValueError) as exc_info:
            Person(first_name="John", last_name="Doe", full_name="Jane Doe")

        error_message = str(exc_info.value)
        assert "full_name" in error_message
        assert "Expected: John Doe" in error_message
        assert "Got: Jane Doe" in error_message
        # Should NOT have "Difference:" line
        assert "Difference:" not in error_message

    def test_validation_with_numeric_shows_difference(self) -> None:
        """Test that numeric validation still shows difference."""

        class Rectangle(SymFields):
            width: float = S
            height: float = S
            area: float = lambda width, height: width * height

        with pytest.raises(ValueError) as exc_info:
            Rectangle(width=5, height=4, area=25)

        error_message = str(exc_info.value)
        assert "Difference:" in error_message


class TestLambdaEdgeCases:
    """Test edge cases with lambda support."""

    def test_lambda_with_chained_dependencies(self) -> None:
        """Test lambda that depends on another lambda's output."""

        class Chained(SymFields):
            a: float = S
            b: float = lambda a: a * 2
            c: float = lambda b: b + 10

        ch = Chained(a=5)
        assert ch.a == 5
        assert ch.b == 10
        assert ch.c == 20

    def test_lambda_calling_complex_expression(self) -> None:
        """Test lambda with complex internal logic."""

        class Complex(SymFields):
            value: int = S
            category: str = lambda value: (
                "low" if value < 10 else "medium" if value < 20 else "high"
            )

        c1 = Complex(value=5)
        assert c1.category == "low"

        c2 = Complex(value=15)
        assert c2.category == "medium"

        c3 = Complex(value=25)
        assert c3.category == "high"
