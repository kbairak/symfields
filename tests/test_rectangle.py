import pytest

from symfields import S, SymFields, SymFieldsError


def test_init():
    class Rectangle(SymFields):
        width: float = S
        height: float = S
        area: float = S("width") * S("height")
        __constraints__ = (S("width") >= 0, S("height") >= 0)

    r = Rectangle(width=4.0, height=5.0)
    assert r.__dict__ == {
        "_values": {"width": 4.0, "height": 5.0, "area": 20.0},
        "_supplied": frozenset({"width", "height"}),
    }


def test_init_from_width_and_area():
    class Rectangle(SymFields):
        width: float = S
        height: float = S
        area: float = S("width") * S("height")
        __constraints__ = (S("width") >= 0, S("height") >= 0)

    r = Rectangle(width=4.0, area=20.0)
    assert r.__dict__ == {
        "_values": {"width": 4.0, "height": 5.0, "area": 20.0},
        "_supplied": frozenset({"width", "area"}),
    }


def test_init_underdetermined():
    class Rectangle(SymFields):
        width: float = S
        height: float = S
        area: float = S("width") * S("height")
        __constraints__ = (S("width") >= 0, S("height") >= 0)

    with pytest.raises(SymFieldsError):
        Rectangle(width=4.0)


def test_setattr_computed_field():
    class Rectangle(SymFields):
        width: float = S
        height: float = S
        area: float = S("width") * S("height")
        __constraints__ = (S("width") >= 0, S("height") >= 0)

    r = Rectangle(width=4.0, height=5.0)
    r.height = 6.0
    assert r.area == 24.0
    assert r.__dict__ == {
        "_values": {"width": 4.0, "height": 6.0, "area": 24.0},
        "_supplied": frozenset({"width", "height"}),
    }


def test_setattr_overdetermined_fails():
    class Rectangle(SymFields):
        width: float = S
        height: float = S
        area: float = S("width") * S("height")
        __constraints__ = (S("width") >= 0, S("height") >= 0)

    r = Rectangle(width=4.0, height=5.0)
    pre = r.__dict__.copy()
    with pytest.raises(SymFieldsError):
        r.area = 28.0
    assert r.__dict__ == pre


def test_update_without_keep_fails():
    class Rectangle(SymFields):
        width: float = S
        height: float = S
        area: float = S("width") * S("height")
        __constraints__ = (S("width") >= 0, S("height") >= 0)

    r = Rectangle(width=4.0, height=5.0)
    pre = r.__dict__.copy()
    with pytest.raises(SymFieldsError):
        r.update(area=28.0, keep=())
    assert r.__dict__ == pre


def test_update_with_keep():
    class Rectangle(SymFields):
        width: float = S
        height: float = S
        area: float = S("width") * S("height")
        __constraints__ = (S("width") >= 0, S("height") >= 0)

    r = Rectangle(width=4.0, height=5.0)
    r.update(area=28.0, keep=("width",))
    assert r.height == 7.0
    assert r.__dict__ == {
        "_values": {"width": 4.0, "height": 7.0, "area": 28.0},
        "_supplied": frozenset({"width", "height"}),
    }


def test_init_violates_constraint():
    class Rectangle(SymFields):
        width: float = S
        height: float = S
        area: float = S("width") * S("height")
        __constraints__ = (S("width") >= 0, S("height") >= 0)

    with pytest.raises(SymFieldsError):
        Rectangle(width=-1.0, height=5.0)


def test_update_violates_constraint():
    class Rectangle(SymFields):
        width: float = S
        height: float = S
        area: float = S("width") * S("height")
        __constraints__ = (S("width") >= 0, S("height") >= 0)

    r = Rectangle(width=4.0, height=5.0)
    pre = r.__dict__.copy()
    with pytest.raises(SymFieldsError):
        r.update(area=-20.0, keep=("width",))
    assert r.__dict__ == pre
