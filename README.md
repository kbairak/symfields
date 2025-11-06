# SymFields

## Overview

SymFields is a Python library that lets you define classes with symbolic field relationships that are automatically inverted. Define a rule like `c = a + b`, and the library will figure out how to calculate any field from any combination of the others.

Instead of writing separate methods to calculate different fields, you write the relationships once and SymFields uses symbolic math (via sympy) to solve for whatever you need.

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
    a: float
    b: float
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

## Features

- **Automatic rule inversion**: Write `c = a + b`, get `a = c - b` and `b = c - a` for free
- **Basic arithmetic operations**: Supports `+`, `-`, `*`, `/`
- **Complex expressions**: Handles combined operations like `d = a + b * c`
- **Multiple rules**: Define multiple relationships in a single class
- **Chained dependencies**: Rules that depend on other computed fields
- **Dataclass integration**: Instances behave like dataclasses with nice `repr`, equality, etc.
- **IDE-friendly**: Field annotations enable autocomplete and type checking in your IDE
- **Validation**: Automatically validates that all provided values satisfy the rules

## Examples

### Real-World Examples

**Rectangle Area**
```python
class Rectangle(SymFields):
    width: float
    height: float
    area: float = S('width') * S('height')

Rectangle(width=5.0, height=3.0)  # Rectangle(width=5.0, height=3.0, area=15.0)
Rectangle(area=15.0, width=5.0)   # Rectangle(width=5.0, height=3.0, area=15.0)
```

**Temperature Conversion**
```python
class Temperature(SymFields):
    celsius: float
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

SymFields uses **sympy** for symbolic mathematics to automatically invert your rules.

**At class definition time** (in `__init_subclass__`):
1. Extracts symbolic expressions from field defaults
2. For each rule like `c = a + b`, uses sympy to solve for every variable:
   - `c = a + b` (original)
   - `a = c - b` (inverted)
   - `b = c - a` (inverted)
3. Stores all these solving paths for later use

**At instance creation time** (in `__init__`):
1. Starts with the fields you provide
2. Iteratively tries to solve for unknown fields using the precomputed rules
3. Picks the first rule where all required inputs are available
4. Continues until all fields are computed or no progress can be made
5. Validates that all provided values satisfy the original rules

This preprocessing approach makes the library efficient - equations are only solved once per class, not on every instance creation.

## Development

This project uses `uv` for dependency management and includes a Makefile for common tasks.

**Run tests:**
```bash
make test
```

**Run linting (ruff + ty):**
```bash
make lint
```

**Run ruff only:**
```bash
make ruff
```

**Run type checking only:**
```bash
make ty
```

## TODO

Planned improvements and features:

- [ ] **Publish to PyPI** - Make the package available via `pip install symfields`
- [ ] **Add README badges** - CI status, PyPI version, Python versions, license
- [ ] **Better error messages** - More helpful messages when rules can't be solved or constraints are violated
- [ ] **Test advanced sympy expressions** - Powers, sqrt, trig functions, logarithms
- [ ] **Type stubs (.pyi files)** - Enhanced IDE support with type stub files

## License

MIT License - see [LICENSE](LICENSE) file for details.
