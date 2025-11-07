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
- **Dataclass integration**: Instances behave like dataclasses with nice `repr`, equality, etc.
- **Type checker friendly**: Optional `= S` pattern helps mypy understand dynamic keyword arguments
- **IDE support**: Field annotations enable autocomplete in your IDE
- **Validation**: Automatically validates that all provided values satisfy the rules
- **Flexible rules**: Use sympy expressions (invertible) or lambdas/callables (forward-only) for any type

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

For non-mathematical or forward-only calculations, you can use lambdas or regular functions:

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
```

**Note:** Wrap lambdas/callables with `S()` for type safety. Lambdas are forward-only and cannot be inverted. You cannot solve for `first_name` given `full_name`.

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
2. Validates lambda signatures (parameters must match field names)
3. Stores the equations for solving at instance creation

**At instance creation time** (in `__init__`):
1. Takes the fields you provide as known values
2. **Solves all sympy equations as a system** using `sympy.solve()` with all unknowns at once
   - Example: Given `top_speed` and `distance`, solves for both `acceleration` and `time` simultaneously
   - Filters for real-valued solutions when multiple solutions exist (e.g., complex roots)
3. **Evaluates lambdas iteratively** (forward-only, cannot be inverted)
   - Calculates lambda fields once their dependencies are known
4. **Validates all rules** to ensure consistency
   - Re-evaluates all equations and lambdas with the final values
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
