# SymFields — structured wrappers around sympy

Define Python classes where fields are sympy expressions. Supply any subset of fields — the rest are solved automatically, with constraints enforced.

Full IDE completion for field names and types — powered by `@dataclass_transform`.

## Install

```sh
pip install symfields
```

Requires Python ≥3.11, sympy ≥1.14.

## Quickstart

```python
from symfields import S, SymFields, SymFieldsError


class Square(SymFields):
    length: float = S
    circumference: float = S("length") * 4
    area: float = S("length") ** 2

    __constraints__ = (S("length") >= 0,)


# Init from any single field
s1 = Square(length=5.0)
s2 = Square(circumference=20.0)
s3 = Square(area=25.0)
assert s1 == s2 == s3

s1.length
# 5.0
s1.area
# 25.0


# Mutate — other fields recompute
s1.circumference = 28.0
s1.length   # 7.0
s1.area     # 49.0


# Constraints enforced
Square(area=-16.0)
# SymFieldsError


# Inconsistent overrides fail
s1.area = -16.0
# SymFieldsError, rollback — __dict__ unchanged
```

## Multiple dependencies

```python
class Rectangle(SymFields):
    width: float = S
    height: float = S
    area: float = S("width") * S("height")

    __constraints__ = (S("width") >= 0, S("height") >= 0)


r = Rectangle(width=4.0, height=5.0)
r.area  # 20.0


# update() with explicit keep pins
r.update(area=28.0, keep=("width",))
r.height  # 7.0


# Underdetermined → error
r.area = 28.0
# SymFieldsError (width alone can't solve height × area)
```

## Validation & formatting

```python
from decimal import Decimal
from typing import Annotated


def round_to_2(x):
    return Decimal(x).quantize(Decimal("0.01"))


class Currency(SymFields):
    EUR: Annotated[Decimal, round_to_2] = S
    USD: Annotated[Decimal, round_to_2] = S("EUR") * Decimal("1.2")


Currency(EUR=Decimal("123.456"))
# Currency(EUR=Decimal('123.46'), USD=Decimal('148.15'))
```

Formatting applied after solving — rounded values need not satisfy equations.

## Use-cases

**Geometry** — compute any dimension from any other:
```python
class Cylinder(SymFields):
    radius: float = S
    height: float = S
    volume: float = 3.14159 * S("radius") ** 2 * S("height")

    __constraints__ = (S("radius") >= 0, S("height") >= 0)


# Design from target volume
can = Cylinder(volume=350.0, radius=3.0)
can.height  # ~12.4 cm
```

**Unit conversion chains** — convert between any pair:
```python
class Temperature(SymFields):
    celsius: float = S
    fahrenheit: float = S("celsius") * 9 / 5 + 32
    kelvin: float = S("celsius") + 273.15


Temp(fahrenheit=212.0).celsius   # 100.0
Temp(kelvin=373.15).fahrenheit   # 212.0
```

**Ohm's law** — V, I, R; supply any two:
```python
class Resistor(SymFields):
    voltage: float = S
    current: float = S
    resistance: float = S("voltage") / S("current")

    __constraints__ = (S("current") >= 0, S("resistance") >= 0)


Resistor(voltage=12.0, current=2.0).resistance  # 6.0
Resistor(voltage=12.0, resistance=6.0).current  # 2.0
```

**Financial** — price with tax, tip, discount:
```python
class Bill(SymFields):
    subtotal: float = S
    tip_pct: float = S
    tip: float = S("subtotal") * S("tip_pct") / 100
    total: float = S("subtotal") + S("tip")


# Know what you want to spend, figure out tip
dinner = Bill(total=60.0, tip_pct=15.0)
dinner.subtotal  # ~52.17
```

## Properties & methods

Subclasses can define `@property`, regular methods, classmethods, staticmethods alongside fields. They are excluded from the equation system and `__repr__`.

```python
class Square(SymFields):
    length: float = S
    circumference: float = S("length") * 4
    area: float = S("length") ** 2

    @property
    def title(self):
        return f"Square({self.length})"

    def double_area(self):
        return self.area * 2
```

## How it works

- `__init_subclass__` collects annotated fields with sympy expression defaults
- `S` is a sentinel marking free fields (fields the user must supply)
- `sympy.solve` inverts the system of equations at init and on every mutation
- `__setattr__` delegates to `update()` with `keep=_supplied - {name}`
- `update()` uses all-or-nothing two-stage solving: try with kept values, fall back to updated-only
- Constraints are sympy inequalities checked via `.subs()` on each candidate solution
- `Annotated[Type, fn]` types apply a formatter after solving

