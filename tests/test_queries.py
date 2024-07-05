"""
Test core query capabilities:

-   Join
-   cartesion-product
-   group-by aggregation
"""

from unittest.mock import sentinel

import pytest

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


def test_query_composite():
    r_1 = Row("TABLE_1", T1C1A=sentinel.VALUET1R1CA)
    r_2 = Row("TABLE_2", T2C1A=sentinel.VALUET2R1CA)
    qc = QueryComposite(r_1, r_2)
    assert qc.TABLE_1.T1C1A == sentinel.VALUET1R1CA
    assert qc.TABLE_2.T2C1A == sentinel.VALUET2R1CA

    assert (
        repr(qc)
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
    the_expr = lambda jr: jr.T1.T1C1A
    a = Aggregate(sum, the_expr)
    assert a.add_to_select == {f"_{id(the_expr)}": the_expr}
    from_ = [
        QueryComposite(Row("T1", T1C1A=2)),
        QueryComposite(Row("T1", T1C1A=3)),
        QueryComposite(Row("T1", T1C1A=5)),
    ]
    select = [Row("", **{f"_{id(the_expr)}": the_expr(qc)}) for qc in from_]
    v = a.value(select)
    assert v == 10


### Integration Tests


@pytest.fixture()
def database():
    t1 = Table(
        "values",
        [
            {"c1": 1, "c2": 42.0},
            {"c1": 2, "c2": 3.14},
            {"c1": 3, "c2": 2.72},
        ],
    )
    t2 = Table(
        "names",
        [
            {"code": 1, "name": "Life"},
            {"code": 2, "name": "Pi"},
            {"code": 3, "name": "Ee"},
        ],
    )
    t3 = Table(
        "raw",
        [
            {"group": "1", "value": 1},
            {"group": "1", "value": 1},
            {"group": "2", "value": 2},
            {"group": "2", "value": 3},
        ],
    )
    return t1, t2, t3


def test_join(database):
    values_table, names_table, raw_table = database
    query = (
        Select(name=lambda jr: jr.n.name, value=lambda jr: jr.v.c2)
        .from_(n=names_table, v=values_table)
        .where(lambda jr: jr.n.code == jr.v.c1)
    )
    expected = [
        {"name": "Life", "value": 42.0},
        {"name": "Pi", "value": 3.14},
        {"name": "Ee", "value": 2.72},
    ]
    assert expected == [row._asdict() for row in fetch(query)]


def test_cart_prod(database):
    values_table, names_table, raw_table = database
    cart_prod = Select(STAR).from_(values_table, names_table)
    expected = [
        {"c1": 1, "c2": 42.0, "code": 1, "name": "Life"},
        {"c1": 1, "c2": 42.0, "code": 2, "name": "Pi"},
        {"c1": 1, "c2": 42.0, "code": 3, "name": "Ee"},
        {"c1": 2, "c2": 3.14, "code": 1, "name": "Life"},
        {"c1": 2, "c2": 3.14, "code": 2, "name": "Pi"},
        {"c1": 2, "c2": 3.14, "code": 3, "name": "Ee"},
        {"c1": 3, "c2": 2.72, "code": 1, "name": "Life"},
        {"c1": 3, "c2": 2.72, "code": 2, "name": "Pi"},
        {"c1": 3, "c2": 2.72, "code": 3, "name": "Ee"},
    ]
    assert expected == [row._asdict() for row in fetch(cart_prod)]


def test_group_by(database):
    values_table, names_table, raw_table = database
    query = (
        Select(
            key=lambda c: c.raw.group, value=lambda c: c.raw.value, total=Aggregate(sum, "value")
        )
        .from_(raw_table)
        .group_by("key")
    )
    expected = [
        {"key": "1", "total": 2},
        {"key": "2", "total": 5},
    ]
    assert expected == [row._asdict() for row in fetch(query)]


def test_group_by_2(database):
    values_table, names_table, raw_table = database
    query = (
        Select(key=lambda c: c.raw.group, total=Aggregate(sum, lambda c: c.raw.value))
        .from_(raw_table)
        .group_by("key")
    )
    expected = [
        {"key": "1", "total": 2},
        {"key": "2", "total": 5},
    ]
    assert expected == [row._asdict() for row in fetch(query)]


def test_group_by_3(database):
    values_table, names_table, raw_table = database
    query = (
        Select(total=Aggregate(sum, lambda c: c.raw.value))
        .from_(raw_table)
        .group_by(key=lambda c: c.raw.group)
    )
    expected = [
        {"key": "1", "total": 2},
        {"key": "2", "total": 5},
    ]
    assert expected == [row._asdict() for row in fetch(query)]


def test_exists_not_exists(database):
    values_table, names_table, raw_table = database
    query_found = (
        Select(STAR)
        .from_(names_table)
        .where(
            lambda nc: exists(
                nc,
                Select(STAR)
                .from_(values_table)
                .where(lambda vc: vc.values.c2 == 42.0 and nc.names.code == vc.values.c1),
            )
        )
    )
    expected = [
        {"code": 1, "name": "Life"},
    ]
    assert expected == [row._asdict() for row in fetch(query_found)]

    query_not_found = (
        Select(STAR)
        .from_(names_table)
        .where(
            lambda nc: exists(
                nc,
                Select(STAR)
                .from_(values_table)
                .where(lambda vc: vc.values.c2 == 1337.0 and nc.names.code == vc.values.c1),
            )
        )
    )
    assert [] == [row._asdict() for row in fetch(query_not_found)]


def test_empty_subquery(database):
    values_table, names_table, raw_table = database
    query_found = (
        Select(STAR)
        .from_(names_table)
        .where(
            lambda nc: nc.names.code
            == fetch_first_value(
                Select(name=lambda vc: vc.values.c1)
                .from_(values_table)
                .where(lambda vc: vc.values.c2 == 1337.0)
            )
        )
    )
    assert [] == [row._asdict() for row in fetch(query_found)]


def test_join_on(database):
    values_table, names_table, raw_table = database
    query = (
        Select(name=lambda jr: jr.n.name, value=lambda jr: jr.v.c2)
        .from_(n=names_table)
        .join(v=values_table, on_=lambda jr: jr.n.code == jr.v.c1)
        .where(lambda jr: jr.v.c2 < 42.0)
    )
    expected = [
        # {"name": "Life", "value": 42.0},
        {"name": "Pi", "value": 3.14},
        {"name": "Ee", "value": 2.72},
    ]
    assert expected == [row._asdict() for row in fetch(query)]


def test_join_on_2(database):
    values_table, names_table, raw_table = database
    query = (
        Select(name=lambda jr: jr.n.name, value=lambda jr: jr.values.c2)
        .from_(n=names_table)
        .join(values_table, on_=lambda jr: jr.n.code == jr.values.c1)
    )
    expected = [
        {"name": "Life", "value": 42.0},
        {"name": "Pi", "value": 3.14},
        {"name": "Ee", "value": 2.72},
    ]
    assert expected == [row._asdict() for row in fetch(query)]
