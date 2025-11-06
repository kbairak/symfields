"""SymFields - Symbolic field relationships with automatic inversion."""

import inspect
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Union

from sympy import Eq, Expr, Symbol, solve
from typing_extensions import dataclass_transform

__all__ = ["S", "SymFields"]


class _SentinelSymbol:
    """Sentinel that can also create Symbols when called.

    This dual-purpose object serves as:
    1. A sentinel value for type checking (field: float = S)
    2. A Symbol factory function (S('name') returns Symbol('name'))
    """

    def __call__(self, name: str) -> Symbol:
        """Create a symbolic variable."""
        return Symbol(name)


# Type as Any so it's compatible with any field type annotation
S: Any = _SentinelSymbol()


@dataclass_transform(kw_only_default=True)
class SymFields:
    """Base class for defining classes with symbolic field relationships.

    Fields can have symbolic expressions as defaults, which are automatically
    inverted to solve for unknown fields based on provided values.

    Example:
        class Sum(SymFields):
            a: float = S
            b: float = S
            c: float = S('a') + S('b')

        s = Sum(a=1, b=2)  # c is calculated as 3
        s = Sum(a=1, c=3)  # b is calculated as 2
        s = Sum(b=2, c=3)  # a is calculated as 1

    Note:
        Adding `= S` to providable fields is optional but helps type checkers
        understand that these fields can be passed as keyword arguments.
    """

    # Class-level attributes added by __init_subclass__
    _symfields_rules: dict[str, Union[Expr, Callable[..., Any]]]
    _symfields_rules_by_target: dict[str, list[tuple[Union[Expr, Callable[..., Any]], set[str]]]]

    def __init_subclass__(cls) -> None:
        """Process class definition to extract and invert symbolic rules."""
        # Extract rules: fields with symbolic expressions or callables as defaults
        # Skip fields with S as default (sentinel for type checking)
        cls._symfields_rules = {
            name: getattr(cls, name)
            for name in cls.__annotations__
            if hasattr(cls, name)
            and getattr(cls, name) is not S
            and (isinstance(getattr(cls, name), Expr) or callable(getattr(cls, name)))
        }

        # Validate callable signatures
        for field_name, field_value in cls._symfields_rules.items():
            if callable(field_value) and not isinstance(field_value, Expr):
                parameters = list(inspect.signature(field_value).parameters.values())

                # Validate parameters and extract dependency field names
                for param in parameters:
                    if param.kind in (
                        inspect.Parameter.VAR_POSITIONAL,
                        inspect.Parameter.VAR_KEYWORD,
                    ):
                        raise TypeError(
                            f"Field '{field_name}': callables cannot use *args or **kwargs"
                        )
                    if param.default != inspect.Parameter.empty:
                        raise TypeError(
                            f"Field '{field_name}': callable parameter '{param.name}' "
                            "cannot have default value"
                        )
                    if param.name not in cls.__annotations__:
                        raise TypeError(
                            f"Field '{field_name}': callable parameter '{param.name}' "
                            "is not a defined field"
                        )

        # Build mapping: field -> list of ways to calculate it
        # Each way is: (rule, set of required fields)
        cls._symfields_rules_by_target = {}

        for target_field, rule in cls._symfields_rules.items():
            if isinstance(rule, Expr):
                # Sympy expression: add forward + inverted rules
                expr_symbols = {str(s) for s in rule.free_symbols}

                # Original rule: target = expr
                cls._symfields_rules_by_target.setdefault(target_field, []).append(
                    (rule, expr_symbols)
                )

                # Inverted rules: solve for each symbol in the expression
                for symbol_name in expr_symbols:
                    solutions = solve(Eq(rule, S(target_field)), symbol_name)
                    if solutions:
                        inverted_expr = solutions[0]
                        required = (expr_symbols - {symbol_name}) | {target_field}
                        cls._symfields_rules_by_target.setdefault(symbol_name, []).append(
                            (inverted_expr, required)
                        )

            elif callable(rule):
                # Callable: add forward rule only (no inversion)
                params = inspect.signature(rule).parameters.keys()
                dependency_fields = set(params)
                cls._symfields_rules_by_target.setdefault(target_field, []).append(
                    (rule, dependency_fields)
                )

        # Remove symbolic defaults and sentinels so dataclass doesn't complain
        for name in cls._symfields_rules:
            delattr(cls, name)
        for name in cls.__annotations__:
            if hasattr(cls, name) and getattr(cls, name) is S:
                delattr(cls, name)

        # Make it a dataclass (modifies cls in-place, no need to reassign)
        dataclass(cls)

        # Capture the dataclass __init__
        original_init = cls.__init__

        # Define new __init__ as a closure
        def __init__(self: SymFields, **kwargs: Any) -> None:
            all_fields = set(cls.__annotations__)
            known_fields = set(kwargs)
            unknown_fields = all_fields - known_fields

            # Iteratively solve for unknowns
            while unknown_fields:
                progress = False

                for field in list(unknown_fields):
                    # Check all ways to calculate this field
                    for rule, required_fields in cls._symfields_rules_by_target.get(field, []):
                        if required_fields <= known_fields:
                            # We have all required fields! Calculate it
                            if isinstance(rule, Expr):
                                # Sympy expression - convert using annotation, fallback to float
                                raw_result = rule.subs(
                                    {sym: kwargs[str(sym)] for sym in rule.free_symbols}
                                )
                                field_type = cls.__annotations__[field]
                                try:
                                    result = field_type(raw_result)
                                except (TypeError, ValueError):
                                    result = float(raw_result)
                            elif callable(rule):
                                # Callable - use result directly
                                params = inspect.signature(rule).parameters.keys()
                                call_kwargs = {param: kwargs[param] for param in params}
                                result = rule(**call_kwargs)

                            kwargs[field] = result
                            known_fields.add(field)
                            unknown_fields.remove(field)
                            progress = True
                            break  # Found one way, no need to try others

                if not progress:
                    break  # Can't solve any more

            # Check if we solved everything
            if unknown_fields:
                # Build helpful error message
                provided = ", ".join(f"'{f}'" for f in sorted(known_fields))
                missing = ", ".join(f"'{f}'" for f in sorted(unknown_fields))

                # Show what's needed for each missing field
                suggestions = []
                for field in sorted(unknown_fields):
                    ways = cls._symfields_rules_by_target.get(field, [])
                    if ways:
                        for _, required_fields in ways:
                            still_needed = required_fields - known_fields
                            if still_needed:
                                need_str = ", ".join(f"'{f}'" for f in sorted(still_needed))
                                suggestions.append(
                                    f"  - To calculate '{field}', also provide: {need_str}"
                                )
                                break  # Just show first option per field

                error_lines = [
                    "Cannot calculate all fields with the provided arguments.",
                    f"Provided: {provided}",
                    f"Missing: {missing}",
                ]
                if suggestions:
                    error_lines.append("Suggestions:")
                    error_lines.extend(suggestions)

                raise ValueError("\n".join(error_lines))

            # Validate: re-evaluate original rules and collect all errors
            validation_errors = []
            for target_field, rule in cls._symfields_rules.items():
                if isinstance(rule, Expr):
                    # Sympy expression
                    raw_result = rule.subs({str(s): kwargs[str(s)] for s in rule.free_symbols})
                    field_type = cls.__annotations__[target_field]
                    try:
                        expected = field_type(raw_result)
                    except (TypeError, ValueError):
                        expected = float(raw_result)
                    rule_str = f"{target_field} = {rule!s}"
                elif callable(rule):
                    # Callable
                    params = inspect.signature(rule).parameters.keys()
                    call_kwargs = {param: kwargs[param] for param in params}
                    expected = rule(**call_kwargs)
                    params_str = ", ".join(params)
                    rule_str = f"{target_field} = <callable({params_str})>"

                actual = kwargs[target_field]

                # Compare using math.isclose for numeric types, == for others
                try:
                    is_valid = math.isclose(expected, actual)
                except (TypeError, ValueError):
                    is_valid = (expected == actual)

                if not is_valid:
                    error_info = [
                        f"  Field '{target_field}':",
                        f"    Rule: {rule_str}",
                        f"    Expected: {expected}",
                        f"    Got: {actual}",
                    ]

                    # Try to add difference for numeric types
                    try:
                        diff = abs(expected - actual)
                        error_info.append(f"    Difference: {diff}")
                    except (TypeError, ValueError):
                        pass  # Non-numeric types, skip difference

                    validation_errors.append("\n".join(error_info))

            if validation_errors:
                error_message = (
                    f"Validation failed for {len(validation_errors)} "
                    f"field{'s' if len(validation_errors) > 1 else ''}.\n"
                    + "\n".join(validation_errors)
                )
                raise ValueError(error_message)

            # Call dataclass __init__
            original_init(self, **kwargs)

        cls.__init__ = __init__  # type: ignore[assignment]
