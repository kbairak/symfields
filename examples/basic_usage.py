"""Basic usage examples for SymFields library."""

from symfields import SymFields, S


# Example 1: Simple sum
class Sum(SymFields):
    a: float
    b: float
    c: float = S('a') + S('b')


print("Example 1: Simple Sum")
print("=" * 50)

s1 = Sum(a=1, b=2)
print(f"Sum(a=1, b=2) = {s1}")

s2 = Sum(a=1, c=3)
print(f"Sum(a=1, c=3) = {s2}")

s3 = Sum(b=2, c=3)
print(f"Sum(b=2, c=3) = {s3}")

print()


# Example 2: Rectangle area
class Rectangle(SymFields):
    width: float
    height: float
    area: float = S('width') * S('height')


print("Example 2: Rectangle")
print("=" * 50)

r1 = Rectangle(width=5, height=3)
print(f"Rectangle(width=5, height=3) = {r1}")

r2 = Rectangle(area=15, width=5)
print(f"Rectangle(area=15, width=5) = {r2}")

print()


# Example 3: Temperature conversion (Celsius to Fahrenheit)
class Temperature(SymFields):
    celsius: float
    fahrenheit: float = S('celsius') * 9/5 + 32


print("Example 3: Temperature Conversion")
print("=" * 50)

t1 = Temperature(celsius=0)
print(f"Temperature(celsius=0) = {t1}")

t2 = Temperature(fahrenheit=32)
print(f"Temperature(fahrenheit=32) = {t2}")

t3 = Temperature(celsius=100)
print(f"Temperature(celsius=100) = {t3}")

print()


# Example 4: Multiple rules
class Physics(SymFields):
    distance: float
    speed: float
    time: float = S('distance') / S('speed')
    average_speed: float = S('distance') / S('time')


print("Example 4: Multiple Rules (Distance, Speed, Time)")
print("=" * 50)

p1 = Physics(distance=100, speed=50)
print(f"Physics(distance=100, speed=50) = {p1}")

p2 = Physics(distance=100, time=2)
print(f"Physics(distance=100, time=2) = {p2}")

print()
