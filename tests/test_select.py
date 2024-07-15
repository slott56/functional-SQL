"""
Test ``SELECT`` statement.

-   Join
-   cartesion-product
-   group-by aggregation

These are not fully-isolated unit tests.
They're integration tests of numerous features.
"""

import pytest

from funcsql import *


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
        Select(name=lambda cr: cr.n.name, value=lambda cr: cr.v.c2)
        .from_(n=names_table, v=values_table)
        .where(lambda cr: cr.n.code == cr.v.c1)
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
        Select(name=lambda cr: cr.n.name, value=lambda cr: cr.v.c2)
        .from_(n=names_table)
        .join(v=values_table, on_=lambda cr: cr.n.code == cr.v.c1)
        .where(lambda cr: cr.v.c2 < 42.0)
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
        Select(name=lambda cr: cr.n.name, value=lambda cr: cr.values.c2)
        .from_(n=names_table)
        .join(values_table, on_=lambda cr: cr.n.code == cr.values.c1)
    )
    expected = [
        {"name": "Life", "value": 42.0},
        {"name": "Pi", "value": 3.14},
        {"name": "Ee", "value": 2.72},
    ]
    assert expected == [row._asdict() for row in fetch(query)]


def test_union(database):
    values_table, names_table, raw_table = database
    query = (
        Select(name=lambda cr: cr.names.name, code=lambda cr: cr.names.code)
        .from_(names=names_table)
        .union(
            Select(name=lambda cr: cr.values.c1, code=lambda cr: cr.values.c2).from_(
                values=values_table
            )
        )
    )
    expected = [
        {"name": "Life", "code": 1},
        {"name": "Pi", "code": 2},
        {"name": "Ee", "code": 3},
        {"name": 1, "code": 42.0},
        {"name": 2, "code": 3.14},
        {"name": 3, "code": 2.72},
    ]
    assert expected == [row._asdict() for row in fetch(query)]


def test_select_clone():
    t = Table("t", [{"a": 42}])
    s1 = Select(a=lambda cr: cr.t.a).from_(t)
    s2 = s1.clone()
    results = [r._asdict() for r in fetch(s2)]
    assert results == [{"a": 42}]
