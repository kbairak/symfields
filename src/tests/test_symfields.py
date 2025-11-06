"""Test suite for SymFields library."""

import math

import pytest
from sympy import cos, exp, log, pi, sin, sqrt, tan

from symfields import S, SymFields


class TestBasicArithmetic:
    """Test basic arithmetic operations."""

    def test_sum_forward_calculation(self) -> None:
        """Test calculating c from a and b."""

        class Sum(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") + S("b")

        s = Sum(a=1, b=2)
        assert s.a == 1
        assert s.b == 2
        assert s.c == 3

    def test_sum_backward_calculation_solve_b(self) -> None:
        """Test calculating b from a and c."""

        class Sum(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") + S("b")

        s = Sum(a=1, c=3)
        assert s.a == 1
        assert s.b == 2
        assert s.c == 3

    def test_sum_backward_calculation_solve_a(self) -> None:
        """Test calculating a from b and c."""

        class Sum(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") + S("b")

        s = Sum(b=2, c=3)
        assert s.a == 1
        assert s.b == 2
        assert s.c == 3

    def test_subtraction(self) -> None:
        """Test subtraction operations."""

        class Diff(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") - S("b")

        # Forward: c = a - b
        s1 = Diff(a=5, b=2)
        assert s1.c == 3

        # Backward: a = c + b
        s2 = Diff(c=3, b=2)
        assert s2.a == 5

        # Backward: b = a - c
        s3 = Diff(a=5, c=3)
        assert s3.b == 2

    def test_multiplication(self) -> None:
        """Test multiplication operations."""

        class Product(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") * S("b")

        # Forward: c = a * b
        s1 = Product(a=3, b=4)
        assert s1.c == 12

        # Backward: a = c / b
        s2 = Product(c=12, b=4)
        assert s2.a == 3

        # Backward: b = c / a
        s3 = Product(a=3, c=12)
        assert s3.b == 4

    def test_division(self) -> None:
        """Test division operations."""

        class Ratio(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") / S("b")

        # Forward: c = a / b
        s1 = Ratio(a=12, b=4)
        assert s1.c == 3

        # Backward: a = c * b
        s2 = Ratio(c=3, b=4)
        assert s2.a == 12

        # Backward: b = a / c
        s3 = Ratio(a=12, c=3)
        assert s3.b == 4


class TestComplexExpressions:
    """Test more complex expressions."""

    def test_combined_operations(self) -> None:
        """Test expressions with multiple operations."""

        class Combined(SymFields):
            a: float = S
            b: float = S
            c: float = S
            d: float = S("a") + S("b") * S("c")

        # Forward: d = a + b * c
        s1 = Combined(a=2, b=3, c=4)
        assert s1.d == 14  # 2 + 3*4 = 14

        # Backward: a = d - b * c
        s2 = Combined(d=14, b=3, c=4)
        assert s2.a == 2

    def test_multiple_rules(self) -> None:
        """Test when multiple rules exist."""

        class MultiRule(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") + S("b")
            d: float = S("a") * 2

        # Calculate c and d from a and b
        s1 = MultiRule(a=3, b=4)
        assert s1.c == 7
        assert s1.d == 6

        # Calculate a from d, then b from a and c
        s2 = MultiRule(d=6, c=7)
        assert s2.a == 3
        assert s2.b == 4

    def test_chained_rules(self) -> None:
        """Test when rules depend on each other."""

        class Chained(SymFields):
            a: float = S
            b: float = S("a") * 2
            c: float = S("b") + 3

        # Forward calculation
        s1 = Chained(a=5)
        assert s1.b == 10
        assert s1.c == 13

        # Backward from c
        s2 = Chained(c=13)
        assert s2.b == 10
        assert s2.a == 5

        # From b
        s3 = Chained(b=10)
        assert s3.a == 5
        assert s3.c == 13


class TestValidation:
    """Test validation and error cases."""

    def test_validation_error_on_contradiction(self) -> None:
        """Test that providing contradictory values raises an error."""

        class Sum(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") + S("b")

        with pytest.raises(ValueError, match=r"Validation error.*expected c=3.*got c=4"):
            Sum(a=1, b=2, c=4)

    def test_not_enough_arguments(self) -> None:
        """Test error when not enough fields are provided."""

        class Sum(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") + S("b")

        with pytest.raises(ValueError, match="Not enough arguments"):
            Sum(a=1)

    def test_all_fields_provided_and_valid(self) -> None:
        """Test that providing all fields works if they're consistent."""

        class Sum(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") + S("b")

        s = Sum(a=1, b=2, c=3)
        assert s.a == 1
        assert s.b == 2
        assert s.c == 3

    def test_multiple_missing_fields_error(self) -> None:
        """Test error message lists all unsolvable fields."""

        class Complex(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") + S("b")

        # With no arguments, both b and c cannot be calculated
        with pytest.raises(ValueError, match="Not enough arguments"):
            Complex()


class TestMultipleRulesForSameField:
    """Test cases where a field appears in multiple rules."""

    def test_field_in_multiple_rules_fallback(self) -> None:
        """Test that when one rule can't solve a field, it tries others."""

        class MultiPath(SymFields):
            a: float = S
            b: float = S
            c: float = S
            d: float = S("a") + S("b")  # d depends on a and b
            e: float = S("c") + S("b")  # e depends on c and b

        # If we provide a and b, we can calculate d
        s1 = MultiPath(a=1, b=2, c=3)
        assert s1.d == 3
        assert s1.e == 5

        # If we provide c and e, we can calculate b, then a and d
        s2 = MultiPath(c=3, e=5, a=1)
        assert s2.b == 2
        assert s2.d == 3

    def test_solve_via_alternative_rule(self) -> None:
        """Test solving a field that appears on the right side of multiple rules."""

        class Alternative(SymFields):
            a: float = S
            b: float = S
            c: float = S
            d: float = S("a") + S("b")
            e: float = S("c") + S("b")

        # Provide d, a, e, c to solve for b using either rule
        s = Alternative(a=1, d=3, c=3, e=5)
        assert s.b == 2


class TestDataclassBehavior:
    """Test that SymFields instances behave like dataclasses."""

    def test_repr(self) -> None:
        """Test that instances have a nice repr."""

        class Sum(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") + S("b")

        s = Sum(a=1, b=2)
        repr_str = repr(s)
        assert "Sum" in repr_str
        assert "a=1" in repr_str
        assert "b=2" in repr_str
        assert "c=3" in repr_str

    def test_equality(self) -> None:
        """Test that instances can be compared for equality."""

        class Sum(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") + S("b")

        s1 = Sum(a=1, b=2)
        s2 = Sum(a=1, c=3)
        s3 = Sum(a=2, b=2)

        assert s1 == s2  # Both represent the same values
        assert s1 != s3  # Different values

    def test_field_access(self) -> None:
        """Test that fields can be accessed as attributes."""

        class Sum(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") + S("b")

        s = Sum(a=1, b=2)
        assert hasattr(s, "a")
        assert hasattr(s, "b")
        assert hasattr(s, "c")


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_single_field_no_rules(self) -> None:
        """Test a class with just regular fields, no rules."""

        class Simple(SymFields):
            a: float = S
            b: float = S

        s = Simple(a=1, b=2)
        assert s.a == 1
        assert s.b == 2

    def test_float_precision(self) -> None:
        """Test that float calculations maintain reasonable precision."""

        class Precise(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") / S("b")

        s = Precise(a=1, b=3)
        assert abs(s.c - 0.333333) < 0.0001

    def test_negative_numbers(self) -> None:
        """Test that negative numbers work correctly."""

        class Negative(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") + S("b")

        s = Negative(a=-5, b=3)
        assert s.c == -2

    def test_zero_handling(self) -> None:
        """Test that zero values work correctly."""

        class Zero(SymFields):
            a: float = S
            b: float = S
            c: float = S("a") + S("b")

        s = Zero(a=0, b=5)
        assert s.c == 5

    def test_integer_type_hints(self) -> None:
        """Test that int type hints work too."""

        class IntFields(SymFields):
            a: int = S
            b: int = S
            c: int = S("a") + S("b")

        s = IntFields(a=1, b=2)
        assert s.c == 3
        assert isinstance(s.c, (int, float))


class TestAdvancedMathExpressions:
    """Test advanced sympy mathematical expressions."""

    def test_power_operations(self) -> None:
        """Test expressions with exponents and powers."""

        class PowerCalc(SymFields):
            base: float = S
            exponent: float = S
            result: float = S("base") ** S("exponent")

        # Forward: result = base^exponent
        p1 = PowerCalc(base=2, exponent=3)
        assert p1.result == 8

        # Backward: base = result^(1/exponent)
        p2 = PowerCalc(result=8, exponent=3)
        assert math.isclose(p2.base, 2)

        # Backward: exponent = log(result) / log(base)
        p3 = PowerCalc(base=2, result=8)
        assert math.isclose(p3.exponent, 3)

    def test_square_root(self) -> None:
        """Test expressions with square roots."""

        class SquareRoot(SymFields):
            value: float = S
            square_root: float = sqrt(S("value"))

        # Forward: square_root = sqrt(value)
        s1 = SquareRoot(value=16)
        assert s1.square_root == 4

        # Backward: value = square_root^2
        s2 = SquareRoot(square_root=4)
        assert s2.value == 16

    def test_pythagorean_theorem(self) -> None:
        """Test Pythagorean theorem: c^2 = a^2 + b^2."""

        class RightTriangle(SymFields):
            a: float = S
            b: float = S
            c: float = sqrt(S("a") ** 2 + S("b") ** 2)

        # Forward: c = sqrt(a^2 + b^2)
        t1 = RightTriangle(a=3, b=4)
        assert t1.c == 5

        # Backward: a = sqrt(c^2 - b^2)
        # Note: sympy may return negative solution, so we check absolute value
        t2 = RightTriangle(c=5, b=4)
        assert math.isclose(abs(t2.a), 3)

        # Backward: b = sqrt(c^2 - a^2)
        t3 = RightTriangle(a=3, c=5)
        assert math.isclose(abs(t3.b), 4)

    def test_trigonometric_functions(self) -> None:
        """Test trigonometric functions."""

        class TrigCalc(SymFields):
            angle: float = S
            sine: float = sin(S("angle"))
            cosine: float = cos(S("angle"))

        # Forward: compute sin and cos from angle
        t1 = TrigCalc(angle=0)
        assert math.isclose(t1.sine, 0)
        assert math.isclose(t1.cosine, 1)

        # Test pi/2 radians (90 degrees)
        t2 = TrigCalc(angle=float(pi / 2))
        assert math.isclose(t2.sine, 1, abs_tol=1e-10)
        assert math.isclose(t2.cosine, 0, abs_tol=1e-10)

    def test_exponential_and_logarithm(self) -> None:
        """Test exponential and logarithmic functions."""

        class ExpLog(SymFields):
            x: float = S
            exp_x: float = exp(S("x"))
            log_exp_x: float = log(S("exp_x"))

        # Forward: exp_x = e^x, log_exp_x = log(exp_x) = x
        e1 = ExpLog(x=2)
        assert math.isclose(e1.exp_x, math.e**2)
        assert math.isclose(e1.log_exp_x, 2)

        # Backward: x = log(exp_x)
        e2 = ExpLog(exp_x=math.e**2)
        assert math.isclose(e2.x, 2)
        assert math.isclose(e2.log_exp_x, 2)

    def test_compound_interest(self) -> None:
        """Test compound interest formula: A = P(1 + r)^t."""

        class CompoundInterest(SymFields):
            principal: float = S
            rate: float = S
            time: float = S
            amount: float = S("principal") * (1 + S("rate")) ** S("time")

        # Forward: Calculate final amount
        c1 = CompoundInterest(principal=1000, rate=0.05, time=10)
        assert math.isclose(c1.amount, 1000 * (1.05**10))

        # Backward: Calculate principal needed
        c2 = CompoundInterest(amount=1628.89, rate=0.05, time=10)
        assert math.isclose(c2.principal, 1000, rel_tol=0.01)

    def test_circle_with_pi(self) -> None:
        """Test circle formulas using pi."""

        class Circle(SymFields):
            radius: float = S
            circumference: float = 2 * pi * S("radius")
            area: float = pi * S("radius") ** 2

        # Forward: Calculate circumference and area
        c1 = Circle(radius=5)
        assert math.isclose(c1.circumference, 2 * math.pi * 5)
        assert math.isclose(c1.area, math.pi * 25)

        # Backward: Calculate radius from area
        # Note: sympy may return negative solution, so we check absolute value
        c2 = Circle(area=math.pi * 25)
        assert math.isclose(abs(c2.radius), 5)
        assert math.isclose(abs(c2.circumference), 2 * math.pi * 5)

    def test_tangent_function(self) -> None:
        """Test tangent function: tan = sin/cos."""

        class TanCalc(SymFields):
            angle: float = S
            tangent: float = tan(S("angle"))

        # Forward: tangent = tan(angle)
        t1 = TanCalc(angle=0)
        assert math.isclose(t1.tangent, 0)

        # Test pi/4 radians (45 degrees) where tan = 1
        t2 = TanCalc(angle=float(pi / 4))
        assert math.isclose(t2.tangent, 1)

    def test_combined_advanced_operations(self) -> None:
        """Test combination of multiple advanced operations."""

        class Physics(SymFields):
            velocity: float = S
            time: float = S
            # Distance with exponential decay: d = v * t * e^(-t)
            distance: float = S("velocity") * S("time") * exp(-S("time"))

        # Forward calculation
        p1 = Physics(velocity=10, time=1)
        expected = 10 * 1 * math.e ** (-1)
        assert math.isclose(p1.distance, expected)

        # Backward: solve for velocity given distance and time
        p2 = Physics(distance=expected, time=1)
        assert math.isclose(p2.velocity, 10)
