"""Test suite for __constraints__ feature."""

import math
from decimal import Decimal
from typing import Annotated, Any

import pytest
from sympy import cos, exp, log, pi, sin, sqrt

from symfields import S, SymFields


class TestBasicConstraints:
    """Test basic constraint functionality."""

    def test_simple_positive_constraint(self) -> None:
        """Test constraint that filters to positive solution."""

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") > 0,)

        # With b=4, a could be 2 or -2, but constraint forces a=2
        f = Foo(b=4)
        assert f.a == 2
        assert f.b == 4

    def test_simple_negative_constraint(self) -> None:
        """Test constraint that filters to negative solution."""

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") < 0,)

        # With b=4, a could be 2 or -2, but constraint forces a=-2
        f = Foo(b=4)
        assert f.a == -2
        assert f.b == 4

    def test_constraint_with_forward_calculation(self) -> None:
        """Test that constraints work when calculating forward."""

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") > 0,)

        # Forward calculation: provide a, get b
        f = Foo(a=3)
        assert f.a == 3
        assert f.b == 9

    def test_constraint_violation_on_init(self) -> None:
        """Test that providing a value violating constraint raises error."""

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") > 0,)

        # Providing a=-2 directly violates the constraint
        with pytest.raises(ValueError, match="Constraint violated"):
            Foo(a=-2, b=4)

    def test_no_solutions_satisfy_constraint(self) -> None:
        """Test error when no solutions satisfy the constraint."""

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") > 5,)

        # With b=4, a could be 2 or -2, neither satisfies a > 5
        with pytest.raises(ValueError, match="No solutions satisfy"):
            Foo(b=4)

    def test_multiple_constraints(self) -> None:
        """Test multiple constraints together."""

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (
                S("a") > 0,
                S("a") < 10,
            )

        # With b=4, a=2 satisfies both constraints
        f = Foo(b=4)
        assert f.a == 2

    def test_constraint_with_range(self) -> None:
        """Test constraint that defines a range."""

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (
                S("a") >= 1,
                S("a") <= 3,
            )

        # With b=4, a=2 is in range [1, 3]
        f = Foo(b=4)
        assert f.a == 2


class TestMultivariateConstraints:
    """Test constraints involving multiple fields."""

    def test_constraint_on_sum(self) -> None:
        """Test constraint involving sum of fields."""

        class TwoVars(SymFields):
            x: float
            y: float
            sum_xy: float = S("x") + S("y")

            __constraints__ = (S("x") + S("y") > 5,)

        # x + y = 10, constraint satisfied
        t = TwoVars(x=3, y=7)
        assert t.x == 3
        assert t.y == 7
        assert t.sum_xy == 10

        # x + y = 3, constraint violated
        with pytest.raises(ValueError, match="Constraint violated"):
            TwoVars(x=1, y=2)

    def test_constraint_involving_computed_field(self) -> None:
        """Test constraint that references a computed field."""

        class Computed(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("b") < 100,)

        # a=5, b=25, constraint satisfied
        c = Computed(a=5)
        assert c.a == 5
        assert c.b == 25

        # a=11, b=121, constraint violated
        with pytest.raises(ValueError, match="Constraint violated"):
            Computed(a=11)

    def test_multivariate_with_multiple_unknowns(self) -> None:
        """Test constraint filtering when solving for multiple unknowns."""

        class MultiUnknown(SymFields):
            x: float
            y: float
            z: float = S("x") + S("y")

            __constraints__ = (S("x") > 0,)

        # Provide z=5, y=2, solve for x=3
        m = MultiUnknown(z=5, y=2)
        assert m.x == 3
        assert m.y == 2
        assert m.z == 5

    def test_complex_multivariate_constraint(self) -> None:
        """Test complex constraint with multiple fields."""

        class Complex(SymFields):
            a: float
            b: float
            c: float = S("a") * S("b")

            __constraints__ = (
                S("a") > 0,
                S("b") > 0,
                S("c") < 50,
            )

        # a=3, b=4, c=12, all constraints satisfied
        comp = Complex(a=3, b=4)
        assert comp.c == 12

        # Would violate c < 50
        with pytest.raises(ValueError, match="Constraint violated"):
            Complex(a=10, b=10)


class TestConstraintsWithAdvancedMath:
    """Test constraints with advanced mathematical expressions."""

    def test_constraint_with_sqrt(self) -> None:
        """Test constraint involving square root."""

        class WithSqrt(SymFields):
            x: float
            y: float = S(sqrt(S("x")))

            __constraints__ = (S("x") > 0,)  # Ensure positive for real sqrt

        w = WithSqrt(x=16)
        assert w.x == 16
        assert w.y == 4

    def test_constraint_with_trigonometry(self) -> None:
        """Test constraint with trigonometric functions."""

        class Trig(SymFields):
            angle: float
            sine: float = S(sin(S("angle")))

            __constraints__ = (
                S("angle") >= 0,
                S("angle") <= pi,
            )

        t = Trig(angle=float(pi / 2))
        assert math.isclose(t.sine, 1, abs_tol=1e-10)

    def test_constraint_with_exponential(self) -> None:
        """Test constraint with exponential function."""

        class Exponential(SymFields):
            x: float
            exp_x: float = S(exp(S("x")))

            __constraints__ = (S("x") >= 0,)

        e = Exponential(x=2)
        assert math.isclose(e.exp_x, math.e**2)

    def test_pythagorean_with_constraint(self) -> None:
        """Test Pythagorean theorem with positive constraint."""

        class RightTriangle(SymFields):
            a: float
            b: float
            c: float = S(sqrt(S("a") ** 2 + S("b") ** 2))

            __constraints__ = (
                S("a") > 0,
                S("b") > 0,
            )

        t = RightTriangle(a=3, b=4)
        assert t.c == 5

        # Negative values violate constraint
        with pytest.raises(ValueError, match="Constraint violated"):
            RightTriangle(a=-3, b=4)


class TestConstraintsWithUpdate:
    """Test that constraints work with update() method."""

    def test_update_respects_constraints(self) -> None:
        """Test that update() respects constraints."""

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") > 0,)

        f = Foo(a=2)
        assert f.a == 2
        assert f.b == 4

        # Update b to 9, should solve for a=3 (not -3)
        f.update(b=9)
        assert f.a == 3
        assert f.b == 9

    def test_update_validation_with_constraints(self) -> None:
        """Test that update validates final state against constraints."""

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") > 0,)

        f = Foo(a=2)

        # Try to update to violate constraint
        with pytest.raises(ValueError, match="Constraint violated"):
            f.update(a=-3)

    def test_update_with_multivariate_constraints(self) -> None:
        """Test update with constraints involving multiple fields."""

        class Sum(SymFields):
            x: float
            y: float
            total: float = S("x") + S("y")

            __constraints__ = (S("total") <= 10,)

        s = Sum(x=3, y=5)
        assert s.total == 8

        # Update that satisfies constraint
        s.update(x=4)
        assert s.x == 4
        assert s.total == 9

        # Update that violates constraint
        with pytest.raises(ValueError, match="Constraint violated"):
            s.update(x=6)  # Would make total = 11


class TestConstraintsWithSetattr:
    """Test that constraints work with __setattr__."""

    def test_setattr_respects_constraints(self) -> None:
        """Test that __setattr__ respects constraints."""

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") > 0,)

        f = Foo(a=2)

        # Update via setattr
        f.b = 9
        assert f.a == 3
        assert f.b == 9

    def test_setattr_validates_constraints(self) -> None:
        """Test that __setattr__ validates constraints."""

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") > 0,)

        f = Foo(a=2)

        # Try to set value that violates constraint
        with pytest.raises(ValueError, match="Constraint violated"):
            f.a = -3


class TestConstraintsWithReplace:
    """Test that constraints work with replace() function."""

    def test_replace_respects_constraints(self) -> None:
        """Test that replace() respects constraints."""
        from symfields import replace

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") > 0,)

        f = Foo(a=2)

        # Replace b, should solve for positive a
        f2 = replace(f, b=9)
        assert f2.a == 3
        assert f2.b == 9

        # Original unchanged
        assert f.a == 2
        assert f.b == 4

    def test_replace_validates_constraints(self) -> None:
        """Test that replace() validates constraints."""
        from symfields import replace

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") > 0,)

        f = Foo(a=2)

        # Replace with value violating constraint
        with pytest.raises(ValueError, match="Constraint violated"):
            replace(f, a=-3)


class TestConstraintErrorMessages:
    """Test detailed error messages for constraint violations."""

    def test_error_shows_failed_constraint(self) -> None:
        """Test that error message shows which constraint failed."""

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") > 0,)

        with pytest.raises(ValueError, match=r"a > 0") as exc_info:
            Foo(b=4, a=-2)

        # Check that error message is informative
        error_msg = str(exc_info.value)
        assert "Constraint violated" in error_msg

    def test_error_shows_multiple_failed_constraints(self) -> None:
        """Test error message with multiple constraint violations."""

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (
                S("a") > 0,
                S("a") < 2,
            )

        # a=5 violates a < 2
        with pytest.raises(ValueError, match="Constraint violated"):
            Foo(a=5)

    def test_error_shows_candidate_solutions(self) -> None:
        """Test that error shows candidate solutions when filtering."""

        class Foo(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") > 10,)

        # Neither a=2 nor a=-2 satisfies a > 10
        with pytest.raises(ValueError, match="No solutions satisfy") as exc_info:
            Foo(b=4)

        error_msg = str(exc_info.value)
        # Should mention the constraint
        assert "a > 10" in error_msg


class TestEmptyAndEdgeCaseConstraints:
    """Test edge cases with constraints."""

    def test_empty_constraints(self) -> None:
        """Test that empty constraints work like no constraints."""

        class NoConstraints(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = ()

        # Should pick first solution (likely -2 or 2)
        nc = NoConstraints(b=4)
        assert nc.b == 4
        assert nc.a ** 2 == 4

    def test_no_constraints_attribute(self) -> None:
        """Test class without __constraints__ attribute."""

        class NoAttr(SymFields):
            a: float
            b: float = S("a") ** 2

        # Should work normally
        na = NoAttr(a=2)
        assert na.a == 2
        assert na.b == 4

    def test_constraint_always_true(self) -> None:
        """Test constraint that is always true."""

        class AlwaysTrue(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") ** 2 >= 0,)  # Always true

        # Should work normally
        at = AlwaysTrue(b=4)
        assert at.b == 4

    def test_constraint_always_false(self) -> None:
        """Test constraint that is always false."""

        class AlwaysFalse(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") > S("a"),)  # Always false

        # Should always fail
        with pytest.raises(ValueError):
            AlwaysFalse(b=4)

    def test_single_solution_with_constraint(self) -> None:
        """Test case where equation has single solution that satisfies constraint."""

        class Linear(SymFields):
            a: float
            b: float = S("a") + 1

            __constraints__ = (S("a") > 0,)

        # Linear equation has single solution: a=4
        lin = Linear(b=5)
        assert lin.a == 4
        assert lin.b == 5


class TestConstraintsWithAnnotated:
    """Test constraints work with Annotated types."""

    def test_constraint_with_decimal_cast(self) -> None:
        """Test constraints work with Decimal precision control."""

        def cast_2_places(value: Any) -> Decimal:
            return Decimal(str(value)).quantize(Decimal("0.01"))

        class WithDecimal(SymFields):
            a: float
            b: Annotated[Decimal, cast_2_places] = S("a") ** 2

            __constraints__ = (S("a") > 0,)

        wd = WithDecimal(b=Decimal("4.00"))
        assert wd.a == 2  # Constraint ensures positive solution
        assert wd.b == Decimal("4.00")

    def test_multifield_with_annotated_and_constraints(self) -> None:
        """Test complex case with Annotated types and constraints."""

        def cast_2_places(value: Any) -> Decimal:
            return Decimal(str(value)).quantize(Decimal("0.01"))

        class Price(SymFields):
            subtotal: Decimal
            tax_rate: Decimal
            tax: Annotated[Decimal, cast_2_places] = S("subtotal") * S("tax_rate")
            total: Annotated[Decimal, cast_2_places] = S("subtotal") + S("tax")

            __constraints__ = (
                S("subtotal") >= 0,
                S("tax_rate") >= 0,
                S("tax_rate") <= 1,
            )

        p = Price(subtotal=Decimal("100"), tax_rate=Decimal("0.23"))
        assert p.tax == Decimal("23.00")
        assert p.total == Decimal("123.00")

        # Negative subtotal violates constraint
        with pytest.raises(ValueError, match="Constraint violated"):
            Price(subtotal=Decimal("-10"), tax_rate=Decimal("0.23"))


class TestConstraintsWithLambdas:
    """Test constraints work with lambda fields."""

    def test_constraint_on_lambda_field(self) -> None:
        """Test constraint that references a lambda-computed field."""

        class WithLambda(SymFields):
            a: float
            b: float
            product: float = S(lambda a, b: a * b)

            __constraints__ = (S("product") > 0,)

        # Positive product
        wl = WithLambda(a=2, b=3)
        assert wl.product == 6

        # Negative product violates constraint
        with pytest.raises(ValueError, match="Constraint violated"):
            WithLambda(a=-2, b=3)

    def test_constraint_with_mixed_symbolic_and_lambda(self) -> None:
        """Test constraints in class with both symbolic and lambda fields."""

        class Mixed(SymFields):
            x: float
            y: float = S("x") ** 2
            z: float = S(lambda x, y: x + y)

            __constraints__ = (
                S("x") > 0,
                S("z") < 100,
            )

        m = Mixed(x=5)
        assert m.y == 25
        assert m.z == 30

        # z = x + x^2 > 100 when x is large
        with pytest.raises(ValueError, match="Constraint violated"):
            Mixed(x=10)  # z = 10 + 100 = 110


class TestConstraintEvaluation:
    """Test constraint evaluation edge cases."""

    def test_constraint_with_equality(self) -> None:
        """Test constraint using equality."""

        class WithEquality(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") >= 2,)

        # a=2 satisfies >= 2
        we = WithEquality(b=4)
        assert we.a == 2

    def test_constraint_with_nonpositive(self) -> None:
        """Test constraint with <= or <."""

        class Bounded(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (S("a") <= 0,)

        # Forces negative solution
        b = Bounded(b=4)
        assert b.a == -2

    def test_combined_equality_and_inequality(self) -> None:
        """Test mixing equality and inequality constraints."""

        class Combined(SymFields):
            a: float
            b: float = S("a") ** 2

            __constraints__ = (
                S("a") >= 0,
                S("b") <= 100,
            )

        c = Combined(a=5)
        assert c.b == 25

        # b > 100 violates constraint
        with pytest.raises(ValueError, match="Constraint violated"):
            Combined(a=11)
