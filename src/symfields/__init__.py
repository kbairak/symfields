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
    """Sentinel that can also create Symbols or wrap callables.

    This multi-purpose object serves as:
    1. A sentinel value for type checking (field: float = S)
    2. A Symbol factory function (S('name') returns Symbol('name'))
    3. A callable wrapper for type safety (S(lambda ...) returns the lambda)
    """

    def __call__(self, name_or_callable: Union[str, Callable[..., Any]]) -> Any:
        """Create a symbolic variable or wrap a callable for type safety.

        Args:
            name_or_callable: Either a string to create a Symbol, or a callable to wrap

        Returns:
            Symbol if given a string, or the callable as-is if given a callable
        """
        if isinstance(name_or_callable, str):
            return Symbol(name_or_callable)
        else:
            # Return callable as-is for type safety with mypy
            return name_or_callable


# Type as Any so it's compatible with any field type annotation
S: Any = _SentinelSymbol()


def _extract_real_solution(solutions: Any, unknowns_list: list[str]) -> dict[Symbol, Any]:
    """Extract a real-valued solution from sympy's solve() result.

    Sympy's solve() can return different formats depending on the problem:
    - Empty list: no solution found
    - List of tuples: multiple solutions (e.g., [(2,), (-1-I,), (-1+I,)])
    - Dict: single unique solution {symbol: value}
    - Other formats in edge cases

    This function normalizes the output to a dict and prefers real solutions
    when multiple solutions exist (e.g., filters out complex roots).

    Args:
        solutions: Raw output from sympy.solve()
        unknowns_list: List of unknown field names being solved for

    Returns:
        Dictionary mapping Symbol objects to their solved values
    """
    if not solutions:
        return {}

    if isinstance(solutions, dict):
        return solutions

    if isinstance(solutions, list):
        # Filter for real solutions
        real_solutions = []
        for sol in solutions:
            if isinstance(sol, tuple) and all(
                not hasattr(v, "is_real") or v.is_real is not False for v in sol
            ):
                real_solutions.append(sol)

        # Use the first real solution, or last solution if no real ones
        chosen_solution = real_solutions[0] if real_solutions else solutions[-1]

        # Convert tuple to dict
        if isinstance(chosen_solution, tuple):
            return dict(zip([Symbol(str(s)) for s in unknowns_list], chosen_solution))
        if isinstance(chosen_solution, dict):
            return chosen_solution
        # Shouldn't reach here, but return empty dict as fallback
        return {}

    return {}


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
    def __init_subclass__(cls) -> None:
        """Process class definition to extract symbolic rules and lambdas."""
        equations, lambdas = [], {}
        for name in cls.__annotations__:
            if not hasattr(cls, name):
                continue
            if isinstance(getattr(cls, name), Expr):
                equations.append(Eq(Symbol(name), getattr(cls, name)))
            elif callable(getattr(cls, name)) and getattr(cls, name) is not S:
                func = getattr(cls, name)
                parameters = list(inspect.signature(func).parameters.values())

                # Validate parameters
                for param in parameters:
                    if param.kind in (
                        inspect.Parameter.VAR_POSITIONAL,
                        inspect.Parameter.VAR_KEYWORD,
                    ):
                        raise TypeError(f"Field '{name}': callables cannot use *args or **kwargs")
                    if param.default != inspect.Parameter.empty:
                        raise TypeError(
                            f"Field '{name}': callable parameter '{param.name}' "
                            "cannot have default value"
                        )
                    if param.name not in cls.__annotations__:
                        raise TypeError(
                            f"Field '{name}': callable parameter '{param.name}' "
                            "is not a defined field"
                        )

                dependency_fields = list(inspect.signature(func).parameters.keys())
                lambdas[name] = (func, dependency_fields)
            delattr(cls, name)

        dataclass(cls, frozen=True)
        original_init = cls.__init__

        def __init__(self: SymFields, **kwargs: Any) -> None:
            known_fields = set(kwargs)
            unknown_fields = set(cls.__annotations__) - known_fields

            # Solve sympy equations as a system
            subs = {Symbol(key): value for key, value in kwargs.items()}
            unknowns_list = list(unknown_fields - lambdas.keys())
            solutions_list = solve([eq.subs(subs) for eq in equations], unknowns_list)

            # Extract real-valued solution from sympy's output
            solutions_dict = _extract_real_solution(solutions_list, unknowns_list)

            # Extract solved values (skip if still symbolic or complex)
            for symbol, value in solutions_dict.items():
                # Check if value is still symbolic (couldn't be fully solved)
                if hasattr(value, "free_symbols") and value.free_symbols:
                    continue

                # Check if value is complex and skip it (prefer real solutions)
                if hasattr(value, "is_real") and value.is_real is False:
                    continue

                try:
                    kwargs[str(symbol)] = cls.__annotations__[str(symbol)](value)
                except (TypeError, ValueError):
                    kwargs[str(symbol)] = float(value)
                known_fields.add(str(symbol))
                unknown_fields.remove(str(symbol))

            # Check if sympy couldn't solve everything
            non_lambda_unknowns = unknown_fields - lambdas.keys()
            if non_lambda_unknowns:
                provided = ", ".join(f"'{f}'" for f in sorted(known_fields))
                missing = ", ".join(f"'{f}'" for f in sorted(non_lambda_unknowns))

                raise ValueError(
                    f"Cannot calculate all fields with the provided arguments.\n"
                    f"Provided: {provided}\n"
                    f"Missing: {missing}\n"
                    f"The system of equations is under-determined "
                    f"(not enough equations to solve for all unknowns)."
                )

            # Solve lambdas iteratively
            while unknown_fields:
                progress = False
                for field in list(unknown_fields):
                    func, dependency_fields = lambdas[field]
                    if known_fields >= set(dependency_fields):
                        call_kwargs = {param: kwargs[param] for param in dependency_fields}
                        kwargs[field] = func(**call_kwargs)
                        known_fields.add(field)
                        unknown_fields.remove(field)
                        progress = True
                if not progress:
                    break

            # Check if lambdas couldn't be calculated
            if unknown_fields:
                provided = ", ".join(f"'{f}'" for f in sorted(known_fields))
                missing = ", ".join(f"'{f}'" for f in sorted(unknown_fields))

                # Build suggestions for lambdas
                suggestions = []
                for field in sorted(unknown_fields):
                    func, dependency_fields = lambdas[field]
                    still_needed = set(dependency_fields) - known_fields
                    if still_needed:
                        need_str = ", ".join(f"'{f}'" for f in sorted(still_needed))
                        suggestions.append(f"  - To calculate '{field}', also provide: {need_str}")

                error_lines = [
                    "Cannot calculate all fields with the provided arguments.",
                    f"Provided: {provided}",
                    f"Missing: {missing}",
                ]
                if suggestions:
                    error_lines.append("Suggestions:")
                    error_lines.extend(suggestions)

                raise ValueError("\n".join(error_lines))

            # Validate all equations and lambdas
            validation_errors = []

            # Validate sympy equations
            for eq in equations:
                # Get field name from left-hand side
                field_name = str(eq.lhs)

                # Get all symbols in this equation
                eq_symbols = eq.free_symbols

                # Only substitute values for symbols that are in this equation
                subs_dict = {Symbol(k): v for k, v in kwargs.items() if Symbol(k) in eq_symbols}

                # Substitute and evaluate
                lhs_value = eq.lhs.subs(subs_dict)
                rhs_value = eq.rhs.subs(subs_dict)

                # Convert to floats for comparison
                try:
                    lhs_float = float(lhs_value)
                    rhs_float = float(rhs_value)
                    is_valid = math.isclose(lhs_float, rhs_float)
                except (TypeError, ValueError):
                    # Non-numeric types, use equality
                    is_valid = lhs_value == rhs_value
                    lhs_float, rhs_float = lhs_value, rhs_value

                if not is_valid:
                    error_info = [
                        f"  Field '{field_name}':",
                        f"    Rule: {field_name} = {eq.rhs}",
                        f"    Expected: {rhs_float}",
                        f"    Got: {lhs_float}",
                    ]

                    # Try to add difference for numeric types
                    try:
                        diff = abs(lhs_float - rhs_float)
                        error_info.append(f"    Difference: {diff}")
                    except (TypeError, ValueError):
                        pass  # Non-numeric types, skip difference

                    validation_errors.append("\n".join(error_info))

            # Validate lambdas
            for field_name, (func, dependency_fields) in lambdas.items():
                expected = func(**{param: kwargs[param] for param in dependency_fields})
                actual = kwargs[field_name]

                # Compare using math.isclose for numeric types, == for others
                try:
                    is_valid = math.isclose(expected, actual)
                except (TypeError, ValueError):
                    is_valid = expected == actual

                if not is_valid:
                    params_str = ", ".join(dependency_fields)
                    error_info = [
                        f"  Field '{field_name}':",
                        f"    Rule: {field_name} = <callable({params_str})>",
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
                field_word = "field" if len(validation_errors) == 1 else "fields"
                error_message = (
                    f"Validation failed for {len(validation_errors)} {field_word}.\n"
                    + "\n".join(validation_errors)
                )
                raise ValueError(error_message)

            original_init(self, **kwargs)

        cls.__init__ = __init__  # type: ignore[assignment]
