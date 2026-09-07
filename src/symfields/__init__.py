from collections.abc import Iterable
from typing import (
    Annotated,
    Any,
    ClassVar,
    dataclass_transform,
    get_args,
    get_origin,
    get_type_hints,
)

import sympy


class SymFieldsError(ValueError):
    pass


class _SMarker:
    def __call__(self, name: str) -> sympy.Symbol:
        return sympy.Symbol(name)


S: Any = _SMarker()


def _resolve(fields, constraints, known):
    syms = {name: sympy.Symbol(name) for name in fields}
    eqs = []
    for name, expr in fields.items():
        if name in known:
            eqs.append(sympy.Eq(syms[name], known[name]))
        if expr is not None:
            eqs.append(sympy.Eq(syms[name], expr))
    sols = sympy.solve(eqs, list(syms.values()), dict=True)
    valid = []
    for sol in sols:
        try:
            if any(
                syms[name] not in sol or sol[syms[name]].free_symbols for name in fields
            ):
                continue
            if not all(bool(c.subs(sol)) for c in constraints):
                continue
            valid.append({name: float(sol[syms[name]]) for name in fields})
        except (TypeError, ValueError):
            continue
    if len(valid) == 1:
        return valid[0]
    raise SymFieldsError(f"Expected 1 solution, found {len(valid)}")


def _convert(hint, value):
    origin = get_origin(hint)
    if origin is Annotated:
        args = get_args(hint)
        return args[1](value)
    return hint(value)


@dataclass_transform(kw_only_default=True)
class SymFields:
    __fields__: ClassVar[dict[str, Any]]
    __hints__: ClassVar[dict[str, Any]]
    __constraints__: ClassVar[tuple[Any, ...]]
    _values: dict[str, Any]
    _supplied: frozenset[str]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        hints = get_type_hints(cls, include_extras=True)
        fields = {}
        cls.__hints__ = {}
        for name, hint in hints.items():
            if name.startswith("_") or get_origin(hint) is ClassVar:
                continue
            raw_default = cls.__dict__.get(name)
            if isinstance(raw_default, (property, classmethod, staticmethod)):
                continue
            if callable(raw_default) and not isinstance(raw_default, _SMarker):
                continue
            if raw_default is None:
                raise SymFieldsError(f"Field {name} has no default value")
            if raw_default is S:
                expr = None
            else:
                expr = sympy.sympify(raw_default)
            fields[name] = expr
            cls.__hints__[name] = hint
            delattr(cls, name)
        cls.__fields__ = fields
        cls.__constraints__ = tuple(cls.__dict__.get("__constraints__", ()))

    def __init__(self, **kwargs):
        cls = type(self)
        for k in kwargs:
            if k not in cls.__fields__:
                raise SymFieldsError(f"Unknown field: {k}")
        known = {n: float(v) for n, v in kwargs.items()}
        raw = _resolve(cls.__fields__, cls.__constraints__, known)
        values = {n: _convert(cls.__hints__[n], raw[n]) for n in cls.__fields__}
        object.__setattr__(self, "_values", values)
        object.__setattr__(self, "_supplied", frozenset(kwargs))

    def update(self, keep: Iterable[str] = (), **kwargs) -> None:
        cls = type(self)
        for k in kwargs:
            if k not in cls.__fields__:
                raise SymFieldsError(f"Unknown field: {k}")
        known = {n: float(v) for n, v in kwargs.items()}
        full = {**{n: float(self._values[n]) for n in keep}, **known}
        try:
            raw = _resolve(cls.__fields__, cls.__constraints__, full)
        except SymFieldsError:
            raw = _resolve(cls.__fields__, cls.__constraints__, known)
        values = {n: _convert(cls.__hints__[n], raw[n]) for n in cls.__fields__}
        object.__setattr__(self, "_values", values)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in type(self).__fields__:
            self.update(**{name: value}, keep=self._supplied - {name})
        else:
            object.__setattr__(self, name, value)

    def __getattr__(self, name: str) -> Any:
        if name in type(self).__fields__:
            return self._values[name]
        raise AttributeError(name)

    def __eq__(self, other) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self._values == other._values

    def __repr__(self) -> str:
        cls = type(self)
        supplied = self._supplied
        ordered = [n for n in cls.__fields__ if n in supplied] + [
            n for n in cls.__fields__ if n not in supplied
        ]
        return (
            f"{cls.__name__}({', '.join(f'{n}={self._values[n]!r}' for n in ordered)})"
        )
