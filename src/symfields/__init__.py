"""SymFields - Symbolic field relationships with automatic inversion."""

import math
from dataclasses import dataclass

from sympy import Eq, Expr, solve
from sympy import Symbol as S

__all__ = ["SymFields", "S"]


class SymFields:
    """Base class for defining classes with symbolic field relationships.

    Fields can have symbolic expressions as defaults, which are automatically
    inverted to solve for unknown fields based on provided values.

    Example:
        class Sum(SymFields):
            a: float
            b: float
            c: float = S('a') + S('b')

        s = Sum(a=1, b=2)  # c is calculated as 3
        s = Sum(a=1, c=3)  # b is calculated as 2
        s = Sum(b=2, c=3)  # a is calculated as 1
    """

    def __init_subclass__(cls):
        """Process class definition to extract and invert symbolic rules."""
        # Extract rules: fields with symbolic expressions as defaults
        cls._symfields_rules = {
            name: value
            for name in cls.__annotations__
            if hasattr(cls, name) and isinstance(value := getattr(cls, name), Expr)
        }

        # Build mapping: field -> list of ways to calculate it
        # Each way is: (expression, set of required fields)
        cls._symfields_rules_by_target = {}

        for target_field, expr in cls._symfields_rules.items():
            expr_symbols = {str(s) for s in expr.free_symbols}

            # Original rule: target = expr
            cls._symfields_rules_by_target.setdefault(target_field, []).append((expr, expr_symbols))

            # Inverted rules: solve for each symbol in the expression
            for symbol_name in expr_symbols:
                solutions = solve(Eq(expr, S(target_field)), symbol_name)
                if solutions:
                    inverted_expr = solutions[0]
                    required = (expr_symbols - {symbol_name}) | {target_field}
                    cls._symfields_rules_by_target.setdefault(symbol_name, []).append(
                        (inverted_expr, required)
                    )

        # Remove symbolic defaults so dataclass doesn't complain
        for name in cls._symfields_rules:
            delattr(cls, name)

        # Make it a dataclass (modifies cls in-place, no need to reassign)
        dataclass(cls)

        # Capture the dataclass __init__
        original_init = cls.__init__

        # Define new __init__ as a closure
        def __init__(self, **kwargs):
            all_fields = set(cls.__annotations__)
            known_fields = set(kwargs)
            unknown_fields = all_fields - known_fields

            # Iteratively solve for unknowns
            while unknown_fields:
                progress = False

                for field in list(unknown_fields):
                    # Check all ways to calculate this field
                    for expr, required_fields in cls._symfields_rules_by_target.get(field, []):
                        if required_fields <= known_fields:
                            # We have all required fields! Calculate it
                            kwargs[field] = float(
                                expr.subs({sym: kwargs[str(sym)] for sym in expr.free_symbols})
                            )
                            known_fields.add(field)
                            unknown_fields.remove(field)
                            progress = True
                            break  # Found one way, no need to try others

                if not progress:
                    break  # Can't solve any more

            # Check if we solved everything
            if unknown_fields:
                fields_str = ", ".join(f"'{f}'" for f in sorted(unknown_fields))
                raise ValueError(f"Not enough arguments to calculate fields {fields_str}")

            # Validate: re-evaluate original rules
            for target_field, expr in cls._symfields_rules.items():
                expected = float(expr.subs({str(s): kwargs[str(s)] for s in expr.free_symbols}))
                if not math.isclose(expected, kwargs[target_field]):
                    raise ValueError(
                        f"Validation error, expected {target_field}={expected}, "
                        f"got {target_field}={kwargs[target_field]}"
                    )

            # Call dataclass __init__
            original_init(self, **kwargs)

        cls.__init__ = __init__
