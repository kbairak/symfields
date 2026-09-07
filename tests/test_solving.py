import pytest

from symfields import S, SymFields, SymFieldsError


def test_unique_solution_from_source():
    class Unsigned(SymFields):
        x: float = S
        y: float = S("x") ** 2

    u = Unsigned(x=2.0)
    assert u.__dict__ == {
        "_values": {"x": 2.0, "y": 4.0},
        "_supplied": frozenset({"x"}),
    }


def test_ambiguous_solution_rejected():
    class Unsigned(SymFields):
        x: float = S
        y: float = S("x") ** 2

    with pytest.raises(SymFieldsError):
        Unsigned(y=4.0)


def test_ambiguous_update_rejected():
    class Unsigned(SymFields):
        x: float = S
        y: float = S("x") ** 2

    u = Unsigned(x=2.0)
    pre = u.__dict__.copy()
    with pytest.raises(SymFieldsError):
        u.y = 9.0
    assert u.__dict__ == pre
