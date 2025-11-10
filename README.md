# SymFields

## Overview

SymFields is a Python library that lets you define classes with symbolic field relationships that are automatically inverted. Define a rule like `c = a + b`, and the library will figure out how to calculate any field from any combination of the others.

Instead of writing separate methods to calculate different fields, you write the relationships once and SymFields uses symbolic math (via [sympy](https://www.sympy.org/)) to solve for whatever you need.

## Installation

Using `uv`:
```bash
uv add symfields
```

Using `pip`:
```bash
pip install symfields
```

## Quick Start

```python
from symfields import SymFields, S

class Sum(SymFields):
    a: float = S
    b: float = S
    c: float = S('a') + S('b')

# Calculate c from a and b
s = Sum(a=1.0, b=2.0)
# Sum(a=1.0, b=2.0, c=3.0)

# Calculate b from a and c
s = Sum(a=1.0, c=3.0)
# Sum(a=1.0, b=2.0, c=3.0)

# Calculate a from b and c
s = Sum(b=2.0, c=3.0)
# Sum(a=1.0, b=2.0, c=3.0)
```

**Note:** Adding `= S` to fields is optional but recommended - it helps type checkers (like mypy) understand that these fields can be provided as keyword arguments. The library works identically either way.

## Features

- **Automatic rule inversion**: Write `c = a + b`, get `a = c - b` and `b = c - a` for free
- **Basic arithmetic operations**: Supports `+`, `-`, `*`, `/`
- **Complex expressions**: Handles combined operations like `d = a + b * c`
- **Multiple rules**: Define multiple relationships in a single class
- **Chained dependencies**: Rules that depend on other computed fields
- **Constraints**: Use `__constraints__` to filter solutions (e.g., enforce `a > 0` when solving `a² = b`)
- **Dataclass integration**: Instances behave like dataclasses with nice `repr`, equality, etc.
- **Type checker friendly**: Optional `= S` pattern helps mypy understand dynamic keyword arguments
- **IDE support**: Field annotations enable autocomplete in your IDE
- **Validation**: Automatically validates that all provided values satisfy the rules and constraints
- **Flexible rules**: Use sympy expressions (invertible) or lambdas/callables (forward-only) for any type
- **Precision control**: Use `Annotated` types with custom cast functions to control decimal precision and rounding
- **Field updates**: Use `.update()`, direct assignment (`obj.field = value`), or `replace(obj, field=value)` for updates

## Examples

### Real-World Examples

**Rectangle Area**
```python
class Rectangle(SymFields):
    width: float = S
    height: float = S
    area: float = S('width') * S('height')

Rectangle(width=5.0, height=3.0)  # Rectangle(width=5.0, height=3.0, area=15.0)
Rectangle(area=15.0, width=5.0)   # Rectangle(width=5.0, height=3.0, area=15.0)
```

**Temperature Conversion**
```python
class Temperature(SymFields):
    celsius: float = S
    fahrenheit: float = S('celsius') * 9/5 + 32

Temperature(celsius=0.0)       # Temperature(celsius=0.0, fahrenheit=32.0)
Temperature(fahrenheit=32.0)   # Temperature(celsius=0.0, fahrenheit=32.0)
```

**Physics - Motion with Acceleration**
```python
class Motion(SymFields):
    acceleration: float
    time: float
    top_speed: float = S('acceleration') * S('time')
    distance: float = 0.5 * S('acceleration') * S('time') ** 2

Motion(acceleration=10.0, time=5.0)
# Motion(acceleration=10.0, time=5.0, top_speed=50.0, distance=125.0)

Motion(top_speed=50.0, time=5.0)
# Motion(acceleration=10.0, time=5.0, top_speed=50.0, distance=125.0)

Motion(distance=125.0, time=5.0)
# Motion(acceleration=10.0, time=5.0, top_speed=50.0, distance=125.0)
```

### Advanced Usage

**Multiple Rules**
```python
import math

class Circle(SymFields):
    radius: float
    diameter: float = S('radius') * 2
    circumference: float = S('radius') * 2 * math.pi
    area: float = S('radius') ** 2 * math.pi

# Provide any field, compute the rest
Circle(radius=5.0)
Circle(diameter=10.0)
Circle(circumference=31.41592653589793)
```

**Chained Dependencies**
```python
class Chained(SymFields):
    a: float
    b: float = S('a') * 2
    c: float = S('b') + 3

Chained(a=5.0)    # Chained(a=5.0, b=10.0, c=13.0)
Chained(c=13.0)   # Chained(a=5.0, b=10.0, c=13.0)
```

**Lambda/Callable Support**

For non-mathematical or forward-only calculations, you can use lambdas or regular functions. Lambdas can be used both for calculated fields and for default values:

```python
# String manipulation
class Person(SymFields):
    first_name: str = S
    last_name: str = S
    full_name: str = S(lambda first_name, last_name: f"{first_name} {last_name}")

Person(first_name="John", last_name="Doe")
# Person(first_name='John', last_name='Doe', full_name='John Doe')

# Mixed sympy (invertible) and lambda (forward-only)
class Rectangle(SymFields):
    width: float = S
    height: float = S
    area: float = S('width') * S('height')  # Can solve backwards
    label: str = S(lambda width, height: f"{width}x{height}")  # Forward only

Rectangle(width=5, height=4)
# Rectangle(width=5, height=4, area=20.0, label='5x4')

Rectangle(area=20, height=4)  # Uses sympy to solve for width
# Rectangle(width=5.0, height=4, area=20.0, label='5.0x4')

# Lambdas for default values
from datetime import datetime

class Document(SymFields):
    title: str = S
    created_at: datetime = S(lambda: datetime.now())  # Default value
```

**Note:** Wrap lambdas/callables with `S()` for type safety. Lambdas are forward-only and cannot be inverted. You cannot solve for `first_name` given `full_name`.

**Precision Control with Annotated**

Control decimal precision and rounding behavior using Python's `Annotated` type with custom cast functions:

```python
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated

def cast_2_places(value):
    """Round to 2 decimal places."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

class Price(SymFields):
    subtotal: Decimal = S
    tax_rate: Decimal = S
    # Total will always have exactly 2 decimal places
    total: Annotated[Decimal, cast_2_places] = S('subtotal') * (1 + S('tax_rate'))

p = Price(subtotal=Decimal("10.00"), tax_rate=Decimal("0.23"))
# Price(subtotal=Decimal('10.00'), tax_rate=Decimal('0.23'), total=Decimal('12.30'))

# Works with backward solving too
p2 = Price(total=Decimal("12.30"), tax_rate=Decimal("0.23"))
# Price(subtotal=Decimal('10.00'), tax_rate=Decimal('0.23'), total=Decimal('12.30'))
```

You can use different rounding modes and precisions for different fields:

```python
from decimal import ROUND_DOWN, ROUND_UP

def cast_2_down(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

def cast_4_up(value):
    return Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_UP)

class Invoice(SymFields):
    amount: Decimal = S
    tax: Annotated[Decimal, cast_2_down] = S('amount') * Decimal("0.23")
    total: Annotated[Decimal, cast_2_down] = S('amount') + S('tax')
    precise: Annotated[Decimal, cast_4_up] = S('total') * Decimal("1.001")
```

**Note:** The cast function must accept exactly one parameter (the value to cast). It's applied both when solving fields and during validation.

**Constraining Solutions with __constraints__**

When equations have multiple solutions, you can use `__constraints__` to specify which solution is valid. This is particularly useful for equations like `b = a²` where solving for `a` gives both positive and negative solutions:

```python
class Foo(SymFields):
    a: float
    b: float = S('a') ** 2

    __constraints__ = (
        S('a') > 0,
    )

# With b=4, a could be 2 or -2, but constraint forces a=2
f = Foo(b=4)
# Foo(a=2.0, b=4)

# Forward calculation still works
f = Foo(a=3)
# Foo(a=3, b=9.0)
```

Constraints support any inequality or relational expression that sympy can evaluate:

```python
class BoundedValue(SymFields):
    x: float
    y: float = S('x') ** 2

    __constraints__ = (
        S('x') >= 0,      # Greater than or equal
        S('x') < 10,      # Less than
        S('y') <= 100,    # Computed field constraints
    )

BoundedValue(y=25)   # BoundedValue(x=5.0, y=25)
BoundedValue(y=121)  # ValueError: Constraint violated
```

**Multivariate constraints** involving multiple fields are also supported:

```python
class Triangle(SymFields):
    a: float
    b: float
    c: float = S(sqrt(S('a')**2 + S('b')**2))

    __constraints__ = (
        S('a') > 0,
        S('b') > 0,
        S('a') + S('b') > S('c'),  # Triangle inequality
    )
```

**Advanced constraint examples:**

```python
from sympy import sin, cos, pi

class Physics(SymFields):
    angle: float
    velocity: float
    range_distance: float = S('velocity')**2 * sin(2*S('angle')) / 9.81

    __constraints__ = (
        S('angle') >= 0,
        S('angle') <= pi/2,  # Keep angle in first quadrant
        S('velocity') > 0,
    )
```

**How constraints work:**

1. **During solving**: When multiple solutions exist (e.g., `a² = 4` → `a = ±2`), constraints filter to valid solutions
2. **During validation**: After all fields are calculated, constraints are validated on the final state
3. **With updates**: Constraints are respected when using `.update()`, `__setattr__`, or `replace()`

If no solutions satisfy all constraints, a detailed error message shows which constraints failed:

```python
class Foo(SymFields):
    a: float
    b: float = S('a') ** 2
    __constraints__ = (S('a') > 10,)

Foo(b=4)  # ValueError: No solutions satisfy all constraints.
          # Constraints: [a > 10]
          #   Solution {a: -2} failed: a > 10
          #   Solution {a: 2} failed: a > 10
```

**Updating Fields After Creation**

You can update fields after instance creation using the `.update()` method. Changes propagate automatically through the constraint system:

```python
class Temperature(SymFields):
    celsius: float = S
    fahrenheit: float = S("celsius") * 9/5 + 32

temp = Temperature(celsius=0.0)
# Temperature(celsius=0.0, fahrenheit=32.0)

# Update celsius - fahrenheit propagates forward
temp.update(celsius=100.0)
# Temperature(celsius=100.0, fahrenheit=212.0)

# Update fahrenheit - celsius propagates backward
temp.update(fahrenheit=32.0)
# Temperature(celsius=0.0, fahrenheit=32.0)
```

The `.update()` method uses intelligent constraint propagation:
- **Forward propagation**: When you change a field, derived fields that depend on it are recalculated
- **Backward propagation**: When you change a derived field, the system inverts equations to solve for input fields
- **Multi-round propagation**: Changes cascade through long dependency chains automatically

```python
class Chain(SymFields):
    a: int = S
    b: int = S("a") + 1
    c: int = S("b") + 1
    d: int = S("c") + 1

chain = Chain(a=1)  # a=1, b=2, c=3, d=4

# Update c - inverts back to b and a, then forward to d
chain.update(c=10)  # a=8, b=9, c=10, d=11
```

**Direct Field Assignment**

You can also update fields using direct assignment - it's equivalent to calling `.update()`:

```python
temp = Temperature(celsius=0.0)

# Direct assignment - automatically propagates changes
temp.celsius = 100.0  # Equivalent to temp.update(celsius=100.0)
# Temperature(celsius=100.0, fahrenheit=212.0)

temp.fahrenheit = 32.0  # Equivalent to temp.update(fahrenheit=32.0)
# Temperature(celsius=0.0, fahrenheit=32.0)
```

**Immutable Updates with replace()**

For immutable-style updates (like `dataclasses.replace()`), use the `replace()` function:

```python
from symfields import replace

original = Temperature(celsius=0.0)
# Temperature(celsius=0.0, fahrenheit=32.0)

# Create new instance with updated value - original unchanged
new_temp = replace(original, fahrenheit=212.0)

# Original unchanged
assert original.celsius == 0.0
assert original.fahrenheit == 32.0

# New instance has updated values
assert new_temp.celsius == 100.0  # Inverted from fahrenheit
assert new_temp.fahrenheit == 212.0
```

**Complex Financial Calculations**
```python
from decimal import Decimal

class BuyStatement(SymFields):
    total_amount: Decimal
    trade_fee: Decimal
    client_rate: Decimal
    provider_rate: Decimal
    units: Decimal
    commission: Decimal = S('trade_fee') + S('fx_fee')
    fx_fee: Decimal = (S('total_amount') - S('trade_fee')) * (1 - S('client_rate') / S('provider_rate'))
    execution_amount: Decimal = (S('total_amount') - S('commission')) * S('client_rate')
    execution_price: Decimal = S('execution_amount') / S('units')
```

## How It Works

SymFields uses **[sympy](https://www.sympy.org/)** to solve systems of equations automatically.

**At class definition time** (in `__init_subclass__`):
1. Extracts symbolic expressions and lambdas from field defaults
2. Extracts constraints from `__constraints__` if present
3. Validates lambda signatures (parameters must match field names)
4. Validates `Annotated` cast functions (must have exactly one parameter)
5. Stores the equations and constraints for solving at instance creation

**At instance creation time** (in `__init__`):
1. Takes the fields you provide as known values
2. **Solves all sympy equations as a system** using `sympy.solve()` with all unknowns at once
   - Example: Given `top_speed` and `distance`, solves for both `acceleration` and `time` simultaneously
   - Filters for real-valued solutions when multiple solutions exist (e.g., complex roots)
   - **Applies constraint filtering** when multiple solutions exist (e.g., `a² = 4` → filters to `a = 2` if constraint is `a > 0`)
   - Applies `Annotated` cast functions to solved values for precision control
3. **Evaluates lambdas iteratively** (forward-only, cannot be inverted)
   - Calculates lambda fields once their dependencies are known
4. **Validates all rules and constraints** to ensure consistency
   - Re-evaluates all equations and lambdas with the final values
   - Verifies all constraints are satisfied on the final state
   - Applies cast functions during validation to ensure consistency
   - Reports detailed errors if any constraints are violated

This approach handles both simple cases (single equations) and complex cases (systems of equations) with the same straightforward logic.

## Development

This project uses `uv` for dependency management and includes a Makefile for common tasks.

**Run tests:**
```bash
make test
```

**Run linting (ruff + mypy):**
```bash
make lint
```

**Run ruff only:**
```bash
make ruff
```

**Run type checking only:**
```bash
make mypy
```

## TODO

Planned improvements and features:

- [ ] **Publish to PyPI** - Make the package available via `pip install symfields`
- [ ] **Add README badges** - CI status, PyPI version, Python versions, license

## License

MIT License - see [LICENSE](LICENSE) file for details.
