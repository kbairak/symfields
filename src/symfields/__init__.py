"""SymFields - Symbolic field relationships with automatic inversion."""

import inspect
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any, TypeVar, Union, get_args, get_origin

from sympy import Eq, Expr, Symbol, solve
from typing_extensions import dataclass_transform

__all__ = ["S", "SymFields", "replace"]

# TypeVar for replace() to preserve concrete type
T = TypeVar("T", bound="SymFields")


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

    def update(self, **kwargs: Any) -> None:
        """Update field values and propagate changes through the constraint system."""
        ...  # Implementation added by __init_subclass__

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute and propagate changes through constraint system."""
        ...  # Implementation added by __init_subclass__

    def __init_subclass__(cls) -> None:
        """Process class definition to extract symbolic rules and lambdas."""
        # Validate Annotated fields first
        for name, annotation in cls.__annotations__.items():
            if get_origin(annotation) is Annotated:
                args = get_args(annotation)

                # Must have exactly 2 args: type and callable
                if len(args) != 2:
                    raise TypeError(
                        f"Field '{name}': Annotated must have exactly 2 arguments "
                        f"(type and callable), got {len(args)}"
                    )

                _base_type, cast_func = args

                # Second arg must be callable
                if not callable(cast_func):
                    raise TypeError(
                        f"Field '{name}': second argument of Annotated must be callable, "
                        f"got {type(cast_func).__name__}"
                    )

                # Must have exactly 1 parameter (no optional parameters allowed)
                sig = inspect.signature(cast_func)
                params = list(sig.parameters.values())

                if len(params) != 1:
                    raise TypeError(
                        f"Field '{name}': cast function must have exactly 1 required parameter, "
                        f"got {len(params)}"
                    )

        # Extract constraints if present
        constraints = tuple()
        if hasattr(cls, "__constraints__"):
            constraints = tuple(cls.__constraints__)
            delattr(cls, "__constraints__")

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

        dataclass(cls, frozen=False)
        original_init = cls.__init__

        def __init__(self: SymFields, **kwargs: Any) -> None:
            known_fields = set(kwargs)
            unknown_fields = set(cls.__annotations__) - known_fields

            # Solve sympy equations as a system
            subs = {Symbol(key): value for key, value in kwargs.items()}
            unknowns_list = list(unknown_fields - lambdas.keys())
            solutions_list = solve([eq.subs(subs) for eq in equations], unknowns_list)

            # Apply constraint filtering if constraints are defined
            # Only filter when there are multiple solutions; single solutions are validated later
            # Note: if solutions_list is a dict (single solution), don't filter
            if constraints and solutions_list and isinstance(solutions_list, list) and len(solutions_list) > 1:
                filtered_solutions = []
                failed_info = []

                for solution in solutions_list:
                    # Convert tuple solution to dict for constraint checking
                    if isinstance(solution, tuple):
                        solution_dict = dict(zip([Symbol(s) for s in unknowns_list], solution))
                    elif isinstance(solution, dict):
                        solution_dict = solution
                    else:
                        # Skip solutions we can't process
                        continue

                    # Merge known values with the candidate solution for constraint checking
                    complete_solution = {**subs, **solution_dict}

                    # Check all constraints for this solution
                    all_satisfied = True
                    failed_constraints = []

                    for constraint in constraints:
                        try:
                            result = constraint.subs(complete_solution)
                            # Evaluate the constraint - be strict
                            if result is False or (hasattr(result, '__bool__') and not bool(result)):
                                all_satisfied = False
                                failed_constraints.append(str(constraint))
                        except Exception:
                            # If we can't evaluate, be conservative and reject
                            all_satisfied = False
                            failed_constraints.append(str(constraint))

                    if all_satisfied:
                        filtered_solutions.append(solution)  # Keep original format
                    elif failed_constraints:
                        failed_info.append(
                            f"  Solution {solution_dict} failed: {', '.join(failed_constraints)}"
                        )

                if not filtered_solutions:
                    constraint_str = ', '.join(str(c) for c in constraints)
                    error_msg = (
                        f"No solutions satisfy all constraints.\n"
                        f"Constraints: [{constraint_str}]"
                    )
                    if failed_info:
                        error_msg += "\n" + "\n".join(failed_info)
                    raise ValueError(error_msg)

                solutions_list = filtered_solutions

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

                field_name = str(symbol)
                annotation = cls.__annotations__[field_name]

                # Check if using Annotated with cast function
                if get_origin(annotation) is Annotated:
                    _base_type, cast_func = get_args(annotation)
                    kwargs[field_name] = cast_func(value)
                else:
                    # Current behavior
                    try:
                        kwargs[field_name] = annotation(value)
                    except (TypeError, ValueError):
                        kwargs[field_name] = float(value)
                known_fields.add(field_name)
                unknown_fields.remove(field_name)

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
            _validate_fields(kwargs)

            original_init(self, **kwargs)

        def update(self: SymFields, **kwargs: Any) -> None:
            """Update field values and propagate changes through the constraint system.

            Args:
                **kwargs: Field values to update

            Raises:
                ValueError: If update would create inconsistent or underconstrained state
            """
            # Validate that all kwargs are valid fields
            for field in kwargs:
                if field not in cls.__annotations__:
                    raise ValueError(f"Field '{field}' is not defined in {cls.__name__}")

            # Start with current values + updates
            values = {field: getattr(self, field) for field in cls.__annotations__}
            values.update(kwargs)
            changed = set(kwargs.keys())

            # Propagation loop - forward and backward passes
            max_iterations = 100  # Safety limit
            for _iteration in range(max_iterations):
                progress = False

                # Forward pass: solve for LHS fields that aren't changed yet
                for eq in equations:
                    lhs_field = str(eq.lhs)
                    eq_symbols = {str(s) for s in eq.free_symbols}
                    rhs_symbols = eq_symbols - {lhs_field}

                    # Forward: if LHS unchanged and all RHS known and at least one RHS changed
                    if (
                        lhs_field not in changed
                        and all(s in values for s in rhs_symbols)
                        and any(s in changed for s in rhs_symbols)
                    ):
                        # Substitute and solve
                        subs = {Symbol(k): values[k] for k in rhs_symbols}
                        new_value = eq.rhs.subs(subs)

                        # Check if value is still symbolic
                        if hasattr(new_value, "free_symbols") and new_value.free_symbols:
                            continue

                        # Check if value is complex
                        if hasattr(new_value, "is_real") and new_value.is_real is False:
                            continue

                        # Apply cast function if using Annotated
                        annotation = cls.__annotations__[lhs_field]
                        if get_origin(annotation) is Annotated:
                            _base_type, cast_func = get_args(annotation)
                            values[lhs_field] = cast_func(new_value)
                        else:
                            try:
                                values[lhs_field] = annotation(new_value)
                            except (TypeError, ValueError):
                                values[lhs_field] = float(new_value)

                        changed.add(lhs_field)
                        progress = True

                # Backward pass: invert rules where LHS is changed and exactly one RHS is unknown
                for eq in equations:
                    lhs_field = str(eq.lhs)
                    eq_symbols = {str(s) for s in eq.free_symbols}
                    rhs_symbols = eq_symbols - {lhs_field}

                    # If LHS is changed, check for invertible rules
                    if lhs_field in changed:
                        unknown_rhs = rhs_symbols - changed

                        # Exactly one unknown RHS - we can invert
                        if len(unknown_rhs) == 1:
                            unknown_field = next(iter(unknown_rhs))

                            # Substitute known values (changed fields + LHS)
                            known_symbols = (changed & rhs_symbols) | {lhs_field}
                            subs = {Symbol(k): values[k] for k in known_symbols}

                            # Solve for the unknown field
                            solutions_list = solve(eq.subs(subs), Symbol(unknown_field))

                            if solutions_list:
                                # Extract solution
                                if isinstance(solutions_list, list):
                                    # Filter for real solutions
                                    real_solutions = []
                                    for sol in solutions_list:
                                        if not hasattr(sol, "is_real") or sol.is_real is not False:
                                            real_solutions.append(sol)

                                    # Apply constraint filtering if multiple solutions
                                    if constraints and len(real_solutions) > 1:
                                        filtered_solutions = []
                                        for sol in real_solutions:
                                            # Create complete solution for constraint checking
                                            complete_solution = {Symbol(k): v for k, v in values.items()}
                                            complete_solution[Symbol(unknown_field)] = sol

                                            # Check all constraints
                                            all_satisfied = True
                                            for constraint in constraints:
                                                try:
                                                    result = constraint.subs(complete_solution)
                                                    if result is False or (hasattr(result, '__bool__') and not bool(result)):
                                                        all_satisfied = False
                                                        break
                                                except Exception:
                                                    all_satisfied = False
                                                    break

                                            if all_satisfied:
                                                filtered_solutions.append(sol)

                                        if filtered_solutions:
                                            real_solutions = filtered_solutions

                                    solution = (
                                        real_solutions[0] if real_solutions else solutions_list[0]
                                    )
                                else:
                                    solution = solutions_list

                                # Check if solution is still symbolic
                                if hasattr(solution, "free_symbols") and solution.free_symbols:
                                    continue

                                # Check if solution is complex
                                if hasattr(solution, "is_real") and solution.is_real is False:
                                    continue

                                # Apply cast function if using Annotated
                                annotation = cls.__annotations__[unknown_field]
                                if get_origin(annotation) is Annotated:
                                    _base_type, cast_func = get_args(annotation)
                                    values[unknown_field] = cast_func(solution)
                                else:
                                    try:
                                        values[unknown_field] = annotation(solution)
                                    except (TypeError, ValueError):
                                        values[unknown_field] = float(solution)

                                changed.add(unknown_field)
                                progress = True

                # Handle lambdas - forward only
                for field, (func, dependency_fields) in lambdas.items():
                    if field not in changed and all(d in changed for d in dependency_fields):
                        call_kwargs = {param: values[param] for param in dependency_fields}
                        values[field] = func(**call_kwargs)
                        changed.add(field)
                        progress = True

                if not progress:
                    break
            else:
                # Hit max iterations - probably a bug
                raise RuntimeError(
                    f"Update propagation did not converge after {max_iterations} iterations"
                )

            # Check for fields in equations that couldn't be determined
            for eq in equations:
                eq_symbols = {str(s) for s in eq.free_symbols}
                # If equation contains any changed field but not all fields are in changed, error
                if eq_symbols & changed and not (eq_symbols <= changed):
                    unsolved = eq_symbols - changed
                    raise ValueError(
                        f"Cannot determine values for fields {unsolved} - "
                        f"update is ambiguous or under-constrained. "
                        f"Changed fields: {changed}"
                    )

            # Validate all rules with new values
            _validate_fields(values)

            # Update self with new values
            for field, value in values.items():
                object.__setattr__(self, field, value)

        def _validate_fields(values: dict[str, Any]) -> None:
            """Validate that all field values satisfy the defined rules.

            Args:
                values: Dictionary mapping field names to their values

            Raises:
                ValueError: If any validation fails
            """
            validation_errors = []

            # Validate sympy equations
            for eq in equations:
                field_name = str(eq.lhs)
                eq_symbols = eq.free_symbols
                subs_dict = {Symbol(k): v for k, v in values.items() if Symbol(k) in eq_symbols}

                lhs_value = eq.lhs.subs(subs_dict)
                rhs_value = eq.rhs.subs(subs_dict)

                # Apply cast function to rhs_value if field has Annotated type
                annotation = cls.__annotations__[field_name]
                if get_origin(annotation) is Annotated:
                    _base_type, cast_func = get_args(annotation)
                    rhs_value = cast_func(rhs_value)

                # Convert to floats for comparison
                try:
                    lhs_float = float(lhs_value)
                    rhs_float = float(rhs_value)
                    is_valid = math.isclose(lhs_float, rhs_float)
                except (TypeError, ValueError):
                    is_valid = lhs_value == rhs_value
                    lhs_float, rhs_float = lhs_value, rhs_value

                if not is_valid:
                    error_info = [
                        f"  Field '{field_name}':",
                        f"    Rule: {field_name} = {eq.rhs}",
                        f"    Expected: {rhs_float}",
                        f"    Got: {lhs_float}",
                    ]
                    try:
                        diff = abs(lhs_float - rhs_float)
                        error_info.append(f"    Difference: {diff}")
                    except (TypeError, ValueError):
                        pass
                    validation_errors.append("\n".join(error_info))

            # Validate lambdas
            for field_name, (func, dependency_fields) in lambdas.items():
                expected = func(**{param: values[param] for param in dependency_fields})
                actual = values[field_name]

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
                    try:
                        diff = abs(expected - actual)
                        error_info.append(f"    Difference: {diff}")
                    except (TypeError, ValueError):
                        pass
                    validation_errors.append("\n".join(error_info))

            # Validate constraints
            for constraint in constraints:
                # Substitute field values into constraint
                subs_dict = {Symbol(k): v for k, v in values.items()}
                try:
                    result = constraint.subs(subs_dict)
                    # Evaluate the constraint - be strict
                    is_satisfied = result is True or (hasattr(result, '__bool__') and bool(result))

                    if not is_satisfied:
                        error_info = [
                            f"  Constraint violated: {constraint}",
                            f"    Field values: {values}",
                        ]
                        validation_errors.append("\n".join(error_info))
                except Exception as e:
                    # If we can't evaluate the constraint, report it
                    error_info = [
                        f"  Cannot evaluate constraint: {constraint}",
                        f"    Error: {e}",
                        f"    Field values: {values}",
                    ]
                    validation_errors.append("\n".join(error_info))

            if validation_errors:
                field_word = "field" if len(validation_errors) == 1 else "fields"
                error_message = (
                    f"Validation failed for {len(validation_errors)} {field_word}.\n"
                    + "\n".join(validation_errors)
                )
                raise ValueError(error_message)

        def __setattr__(self: SymFields, name: str, value: Any) -> None:
            """Set attribute and propagate changes through constraint system.

            Setting a field triggers the same constraint propagation as .update().

            Args:
                name: Field name to set
                value: New value for the field

            Example:
                temp = Temperature(celsius=0.0)
                temp.celsius = 100.0  # Equivalent to temp.update(celsius=100.0)
            """
            # Check if this is a defined field AND object is already initialized
            # (During __init__, fields don't exist yet, so hasattr returns False)
            if name in cls.__annotations__ and hasattr(self, name):
                # Object is initialized, use update to propagate changes
                self.update(**{name: value})
            else:
                # During initialization or not a SymField - use normal setattr
                object.__setattr__(self, name, value)

        cls.__init__ = __init__  # type: ignore[assignment]
        cls.update = update  # type: ignore[assignment]
        cls.__setattr__ = __setattr__  # type: ignore[assignment]


def replace(obj: T, **kwargs: Any) -> T:
    """Create a new instance with updated fields, mirroring dataclasses.replace().

    This function creates a new instance of the same type as `obj`, with field values
    updated according to `kwargs`. The original instance remains unchanged (immutable pattern).

    Changes propagate through the constraint system using the same forward/backward
    propagation as .update().

    Args:
        obj: The SymFields instance to replace fields on
        **kwargs: Field names and new values

    Returns:
        A new instance of the same type with updated values

    Example:
        >>> temp = Temperature(celsius=0.0)
        >>> new_temp = replace(temp, fahrenheit=212.0)
        >>> temp.celsius  # Original unchanged
        0.0
        >>> new_temp.celsius  # New instance has inverted value
        100.0

    Note:
        Like dataclasses.replace(), this always returns a new instance,
        even if no fields are changed.
    """
    # Create a copy with all current field values
    new_obj = type(obj)(**{field: getattr(obj, field) for field in obj.__annotations__})

    # Update the copy with new values (if any provided)
    if kwargs:
        new_obj.update(**kwargs)

    return new_obj
