"""
Test base features that support queries.

-   Table
-   Row
-   CompositeRow
-   Aggregate
"""

from unittest.mock import sentinel

from funcsql import *


def test_table():
    t = Table(sentinel.NAME, [{"CELL1A": sentinel.VALUE1A}])
    assert t.column_names() == ["CELL1A"]
    assert t.schema == ["CELL1A"]
    assert list(iter(t)) == [Row(sentinel.NAME, CELL1A=sentinel.VALUE1A)]
    assert list(t.alias_iter(sentinel.ALIAS)) == [Row(sentinel.ALIAS, CELL1A=sentinel.VALUE1A)]

    t.load([{"CELL1A": sentinel.NEW1A}])
    assert list(iter(t)) == [Row(sentinel.NAME, CELL1A=sentinel.NEW1A)]


def test_row():
    r = Row(sentinel.TABLE, CELL1A=sentinel.VALUE1A)
    assert r.CELL1A == sentinel.VALUE1A
    assert repr(r) == "Row(sentinel.TABLE, **{'CELL1A': sentinel.VALUE1A})"
    assert r._asdict() == {"CELL1A": sentinel.VALUE1A}
    assert r._values() == [sentinel.VALUE1A]


def test_omposite_row():
    r_1 = Row("TABLE_1", T1C1A=sentinel.VALUET1R1CA)
    r_2 = Row("TABLE_2", T2C1A=sentinel.VALUET2R1CA)
    cr = CompositeRow(r_1, r_2)
    assert cr.TABLE_1.T1C1A == sentinel.VALUET1R1CA
    assert cr.TABLE_2.T2C1A == sentinel.VALUET2R1CA

    assert (
        repr(cr)
        == "{'TABLE_1': Row('TABLE_1', **{'T1C1A': sentinel.VALUET1R1CA}), 'TABLE_2': Row('TABLE_2', **{'T2C1A': sentinel.VALUET2R1CA})}"
    )


def test_aggregate_1():
    a = Aggregate(count, "*")
    assert a.add_to_select != {}
    v = a.value(
        [
            Row("T1", T1C1A=2),
            Row("T1", T1C1A=3),
            Row("T1", T1C1A=5),
        ]
    )
    assert v == 3


def test_aggregate_2():
    a = Aggregate(sum, "T1C1A")
    assert a.add_to_select == {}
    v = a.value(
        [
            Row("T1", T1C1A=2),
            Row("T1", T1C1A=3),
            Row("T1", T1C1A=5),
        ]
    )
    assert v == 10


def test_aggregate_3():
    the_expr = lambda cr: cr.T1.T1C1A
    a = Aggregate(sum, the_expr)
    assert a.add_to_select == {f"_{id(the_expr)}": the_expr}
    from_ = [
        CompositeRow(Row("T1", T1C1A=2)),
        CompositeRow(Row("T1", T1C1A=3)),
        CompositeRow(Row("T1", T1C1A=5)),
    ]
    select = [Row("", **{f"_{id(the_expr)}": the_expr(cr)}) for cr in from_]
    v = a.value(select)
    assert v == 10
