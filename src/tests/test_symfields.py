"""Test suite for SymFields library."""

import pytest

from symfields import S, SymFields


class TestBasicArithmetic:
    """Test basic arithmetic operations."""

    def test_sum_forward_calculation(self):
        """Test calculating c from a and b."""

        class Sum(SymFields):
            a: float
            b: float
            c: float = S("a") + S("b")

        s = Sum(a=1, b=2)
        assert s.a == 1
        assert s.b == 2
        assert s.c == 3

    def test_sum_backward_calculation_solve_b(self):
        """Test calculating b from a and c."""

        class Sum(SymFields):
            a: float
            b: float
            c: float = S("a") + S("b")

        s = Sum(a=1, c=3)
        assert s.a == 1
        assert s.b == 2
        assert s.c == 3

    def test_sum_backward_calculation_solve_a(self):
        """Test calculating a from b and c."""

        class Sum(SymFields):
            a: float
            b: float
            c: float = S("a") + S("b")

        s = Sum(b=2, c=3)
        assert s.a == 1
        assert s.b == 2
        assert s.c == 3

    def test_subtraction(self):
        """Test subtraction operations."""

        class Diff(SymFields):
            a: float
            b: float
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

    def test_multiplication(self):
        """Test multiplication operations."""

        class Product(SymFields):
            a: float
            b: float
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

    def test_division(self):
        """Test division operations."""

        class Ratio(SymFields):
            a: float
            b: float
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

    def test_combined_operations(self):
        """Test expressions with multiple operations."""

        class Combined(SymFields):
            a: float
            b: float
            c: float
            d: float = S("a") + S("b") * S("c")

        # Forward: d = a + b * c
        s1 = Combined(a=2, b=3, c=4)
        assert s1.d == 14  # 2 + 3*4 = 14

        # Backward: a = d - b * c
        s2 = Combined(d=14, b=3, c=4)
        assert s2.a == 2

    def test_multiple_rules(self):
        """Test when multiple rules exist."""

        class MultiRule(SymFields):
            a: float
            b: float
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

    def test_chained_rules(self):
        """Test when rules depend on each other."""

        class Chained(SymFields):
            a: float
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

    def test_validation_error_on_contradiction(self):
        """Test that providing contradictory values raises an error."""

        class Sum(SymFields):
            a: float
            b: float
            c: float = S("a") + S("b")

        with pytest.raises(ValueError, match="Validation error.*expected c=3.*got c=4"):
            Sum(a=1, b=2, c=4)

    def test_not_enough_arguments(self):
        """Test error when not enough fields are provided."""

        class Sum(SymFields):
            a: float
            b: float
            c: float = S("a") + S("b")

        with pytest.raises(ValueError, match="Not enough arguments"):
            Sum(a=1)

    def test_all_fields_provided_and_valid(self):
        """Test that providing all fields works if they're consistent."""

        class Sum(SymFields):
            a: float
            b: float
            c: float = S("a") + S("b")

        s = Sum(a=1, b=2, c=3)
        assert s.a == 1
        assert s.b == 2
        assert s.c == 3

    def test_multiple_missing_fields_error(self):
        """Test error message lists all unsolvable fields."""

        class Complex(SymFields):
            a: float
            b: float
            c: float = S("a") + S("b")

        # With no arguments, both b and c cannot be calculated
        with pytest.raises(ValueError, match="Not enough arguments"):
            Complex()


class TestMultipleRulesForSameField:
    """Test cases where a field appears in multiple rules."""

    def test_field_in_multiple_rules_fallback(self):
        """Test that when one rule can't solve a field, it tries others."""

        class MultiPath(SymFields):
            a: float
            b: float
            c: float
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

    def test_solve_via_alternative_rule(self):
        """Test solving a field that appears on the right side of multiple rules."""

        class Alternative(SymFields):
            a: float
            b: float
            c: float
            d: float = S("a") + S("b")
            e: float = S("c") + S("b")

        # Provide d, a, e, c to solve for b using either rule
        s = Alternative(a=1, d=3, c=3, e=5)
        assert s.b == 2


class TestDataclassBehavior:
    """Test that SymFields instances behave like dataclasses."""

    def test_repr(self):
        """Test that instances have a nice repr."""

        class Sum(SymFields):
            a: float
            b: float
            c: float = S("a") + S("b")

        s = Sum(a=1, b=2)
        repr_str = repr(s)
        assert "Sum" in repr_str
        assert "a=1" in repr_str
        assert "b=2" in repr_str
        assert "c=3" in repr_str

    def test_equality(self):
        """Test that instances can be compared for equality."""

        class Sum(SymFields):
            a: float
            b: float
            c: float = S("a") + S("b")

        s1 = Sum(a=1, b=2)
        s2 = Sum(a=1, c=3)
        s3 = Sum(a=2, b=2)

        assert s1 == s2  # Both represent the same values
        assert s1 != s3  # Different values

    def test_field_access(self):
        """Test that fields can be accessed as attributes."""

        class Sum(SymFields):
            a: float
            b: float
            c: float = S("a") + S("b")

        s = Sum(a=1, b=2)
        assert hasattr(s, "a")
        assert hasattr(s, "b")
        assert hasattr(s, "c")


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_single_field_no_rules(self):
        """Test a class with just regular fields, no rules."""

        class Simple(SymFields):
            a: float
            b: float

        s = Simple(a=1, b=2)
        assert s.a == 1
        assert s.b == 2

    def test_float_precision(self):
        """Test that float calculations maintain reasonable precision."""

        class Precise(SymFields):
            a: float
            b: float
            c: float = S("a") / S("b")

        s = Precise(a=1, b=3)
        assert abs(s.c - 0.333333) < 0.0001

    def test_negative_numbers(self):
        """Test that negative numbers work correctly."""

        class Negative(SymFields):
            a: float
            b: float
            c: float = S("a") + S("b")

        s = Negative(a=-5, b=3)
        assert s.c == -2

    def test_zero_handling(self):
        """Test that zero values work correctly."""

        class Zero(SymFields):
            a: float
            b: float
            c: float = S("a") + S("b")

        s = Zero(a=0, b=5)
        assert s.c == 5

    def test_integer_type_hints(self):
        """Test that int type hints work too."""

        class IntFields(SymFields):
            a: int
            b: int
            c: int = S("a") + S("b")

        s = IntFields(a=1, b=2)
        assert s.c == 3
        assert isinstance(s.c, (int, float))
