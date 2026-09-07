import pytest

from symfields import S, SymFields, SymFieldsError


def test_init_from_length():
    class Square(SymFields):
        length: float = S
        circumference: float = S("length") * 4
        area: float = S("length") ** 2
        __constraints__ = (S("length") >= 0,)

    s = Square(length=5.0)
    assert s.__dict__ == {
        "_values": {"length": 5.0, "circumference": 20.0, "area": 25.0},
        "_supplied": frozenset({"length"}),
    }


def test_init_from_circumference():
    class Square(SymFields):
        length: float = S
        circumference: float = S("length") * 4
        area: float = S("length") ** 2
        __constraints__ = (S("length") >= 0,)

    s = Square(circumference=20.0)
    assert s.__dict__ == {
        "_values": {"length": 5.0, "circumference": 20.0, "area": 25.0},
        "_supplied": frozenset({"circumference"}),
    }


def test_init_from_area():
    class Square(SymFields):
        length: float = S
        circumference: float = S("length") * 4
        area: float = S("length") ** 2
        __constraints__ = (S("length") >= 0,)

    s = Square(area=25.0)
    assert s.__dict__ == {
        "_values": {"length": 5.0, "circumference": 20.0, "area": 25.0},
        "_supplied": frozenset({"area"}),
    }


def test_init_from_area_without_constraints_fails():
    class Square(SymFields):
        length: float = S
        circumference: float = S("length") * 4
        area: float = S("length") ** 2

    with pytest.raises(SymFieldsError):
        Square(area=25.0)


def test_attribute_access():
    class Square(SymFields):
        length: float = S
        circumference: float = S("length") * 4
        area: float = S("length") ** 2
        __constraints__ = (S("length") >= 0,)

    s = Square(length=5.0)
    assert s.circumference == 20.0
    assert s.area == 25.0


def test_equality():
    class Square(SymFields):
        length: float = S
        circumference: float = S("length") * 4
        area: float = S("length") ** 2
        __constraints__ = (S("length") >= 0,)

    assert Square(length=5.0) == Square(circumference=20.0) == Square(area=25.0)
    assert Square(length=5.0) != Square(length=6.0)


def test_repr_supplied_first():
    class Square(SymFields):
        length: float = S
        circumference: float = S("length") * 4
        area: float = S("length") ** 2
        __constraints__ = (S("length") >= 0,)

    assert (
        repr(Square(length=5.0)) == "Square(length=5.0, circumference=20.0, area=25.0)"
    )
    assert (
        repr(Square(area=25.0)) == "Square(area=25.0, length=5.0, circumference=20.0)"
    )


def test_init_consistent_redundant():
    class Square(SymFields):
        length: float = S
        circumference: float = S("length") * 4
        area: float = S("length") ** 2
        __constraints__ = (S("length") >= 0,)

    s = Square(length=5.0, circumference=20.0, area=25.0)
    assert s.__dict__ == {
        "_values": {"length": 5.0, "circumference": 20.0, "area": 25.0},
        "_supplied": frozenset({"length", "circumference", "area"}),
    }


def test_init_inconsistent():
    class Square(SymFields):
        length: float = S
        circumference: float = S("length") * 4
        area: float = S("length") ** 2
        __constraints__ = (S("length") >= 0,)

    with pytest.raises(SymFieldsError):
        Square(length=5.0, circumference=21.0)


def test_init_no_fields():
    class Square(SymFields):
        length: float = S
        circumference: float = S("length") * 4
        area: float = S("length") ** 2
        __constraints__ = (S("length") >= 0,)

    with pytest.raises(SymFieldsError):
        Square()


def test_setattr_length():
    class Square(SymFields):
        length: float = S
        circumference: float = S("length") * 4
        area: float = S("length") ** 2
        __constraints__ = (S("length") >= 0,)

    s = Square(length=5.0)
    s.length = 6.0
    assert s.__dict__ == {
        "_values": {"length": 6.0, "circumference": 24.0, "area": 36.0},
        "_supplied": frozenset({"length"}),
    }


def test_setattr_circumference():
    class Square(SymFields):
        length: float = S
        circumference: float = S("length") * 4
        area: float = S("length") ** 2
        __constraints__ = (S("length") >= 0,)

    s = Square(length=5.0)
    s.circumference = 28.0
    assert s.__dict__["_values"] == {"length": 7.0, "circumference": 28.0, "area": 49.0}
    assert s.__dict__["_supplied"] == frozenset({"length"})


def test_setattr_area():
    class Square(SymFields):
        length: float = S
        circumference: float = S("length") * 4
        area: float = S("length") ** 2
        __constraints__ = (S("length") >= 0,)

    s = Square(length=5.0)
    s.area = 64.0
    assert s.__dict__["_values"] == {"length": 8.0, "circumference": 32.0, "area": 64.0}
    assert s.__dict__["_supplied"] == frozenset({"length"})


def test_setattr_violates_constraint():
    class Square(SymFields):
        length: float = S
        circumference: float = S("length") * 4
        area: float = S("length") ** 2
        __constraints__ = (S("length") >= 0,)

    s = Square(length=5.0)
    pre = s.__dict__.copy()
    with pytest.raises(SymFieldsError):
        s.length = -1.0
    assert s.__dict__ == pre


def test_setattr_unsatisfiable():
    class Square(SymFields):
        length: float = S
        circumference: float = S("length") * 4
        area: float = S("length") ** 2
        __constraints__ = (S("length") >= 0,)

    s = Square(length=5.0)
    pre = s.__dict__.copy()
    with pytest.raises(SymFieldsError):
        s.area = -16.0
    assert s.__dict__ == pre
