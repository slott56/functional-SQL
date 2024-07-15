"""
Test ``WITH`` clause on a ``SELECT`` statement.

-   recursive
-   non-recursive

These are not fully-isolated unit tests.
They're integration tests of numerous features.
"""

import logging

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


from contextlib import nullcontext


def test_with_context_base(database):
    values, names, row = database

    with nullcontext(
        fetch_table("the_codes", Select(code=lambda cr: cr.names.code).from_(names))
    ) as the_codes:
        rows = fetch(Select(STAR).from_(the_codes))

    assert [r._asdict() for r in rows] == [{"code": 1}, {"code": 2}, {"code": 3}]


def test_with_context(database):
    values, names, row = database

    with fetch_table("the_codes", Select(code=lambda cr: cr.names.code).from_(names)) as the_codes:
        rows = fetch(Select(STAR).from_(the_codes))

    assert [r._asdict() for r in rows] == [{"code": 1}, {"code": 2}, {"code": 3}]


def test_with_context_name_resolution(database):
    values, names, row = database

    with pytest.raises(ValueError):
        with fetch_table(
            "the_codes", Select(code=lambda cr: cr.names.code).from_(names)
        ) as the_codes:
            rows = fetch(Select(STAR).from_("the_codes"))


def test_with_simple(database):
    values, names, row = database

    query = With(the_codes=Select(code=lambda cr: cr.names.code).from_(names)).query(
        Select(STAR).from_("the_codes")
    )
    rows = fetch(query)
    assert [r._asdict() for r in rows] == [{"code": 1}, {"code": 2}, {"code": 3}]


def test_with_select(database):
    values, names, row = database

    query = (
        With(the_codes=Select(code=lambda cr: cr.names.code).from_(names))
        .select(STAR)
        .from_("the_codes")
    )
    rows = fetch(query)
    assert [r._asdict() for r in rows] == [{"code": 1}, {"code": 2}, {"code": 3}]

    assert list(query) == list(fetch(query))


def test_with_select_alias(database):
    values, names, row = database

    query = (
        With(the_codes=Select(code=lambda cr: cr.names.code).from_(names))
        .select(STAR)
        .from_(c="the_codes")
    )
    rows = fetch(query)
    assert [r._asdict() for r in rows] == [{"code": 1}, {"code": 2}, {"code": 3}]


def test_with_query_join(database):
    values, names, row = database

    query = With(the_codes=Select(code=lambda cr: cr.names.code).from_(names)).query(
        Select(STAR)
        .from_(c="the_codes")
        .join(table=names, on_=lambda cr: cr.names.code == cr.the_codes.code)
    )
    rows = fetch(query)
    assert [r._asdict() for r in rows] == [
        {"code": 1, "name": "Life"},
        {"code": 2, "name": "Pi"},
        {"code": 3, "name": "Ee"},
    ]


def test_with_select_join(database):
    values, names, row = database

    query = (
        With(the_codes=Select(code=lambda cr: cr.names.code).from_(names))
        .select(STAR)
        .from_(names)
        .join(c="the_codes", on_=lambda cr: cr.names.code == cr.the_codes.code)
    )
    rows = fetch(query)
    assert [r._asdict() for r in rows] == [
        {"code": 1, "name": "Life"},
        {"code": 2, "name": "Pi"},
        {"code": 3, "name": "Ee"},
    ]


def test_with_select_clauses(database):
    values, names, row = database

    query = (
        With(the_codes=Select(code=lambda cr: cr.names.code).from_(names))
        .select(count=Aggregate(count, "c"), c=lambda qc: qc.the_codes.code)
        .from_("the_codes")
        .where(lambda qc: qc.the_codes.code != 0)
        .group_by("c")
        .having(lambda row: row.count > 0)
    )
    rows = fetch(query)
    assert [r._asdict() for r in rows] == [
        {"c": 1, "count": 1},
        {"c": 2, "count": 1},
        {"c": 3, "count": 1},
    ]


@pytest.fixture()
def org_database():
    org = Table(
        "org",
        [
            dict(name="Alice", boss=None),
            dict(name="Bob", boss="Alice"),
            dict(name="Cindy", boss="Alice"),
            dict(name="Dave", boss="Bob"),
            dict(name="Emma", boss="Bob"),
            dict(name="Fred", boss="Cindy"),
            dict(name="Gail", boss="Cindy"),
        ],
    )
    return org


def test_with_recursive_values(org_database, caplog):
    """Breadth-First
    See https://www.sqlite.org/lang_with.html

    ..  code-block:: SQL

        WITH RECURSIVE
          under_alice(name,level) AS (
            VALUES('Alice',0)
            UNION ALL
            SELECT org.name, under_alice.level+1
              FROM org JOIN under_alice ON org.boss=under_alice.name
             ORDER BY 2
          )
        SELECT substr('..........',1,level*3) || name FROM under_alice;
    """
    caplog.set_level(logging.DEBUG)
    org = org_database
    query = (
        With(
            under_alice=Values(name=lambda cr: "Alice", level=lambda cr: 0).union(
                Select(name=lambda cr: cr.org.name, level=lambda cr: cr.under_alice.level + 1)
                .from_(org)
                .join(table="under_alice", on_=lambda cr: cr.org.boss == cr.under_alice.name)
            )
        )
        .select(line=lambda cr: ".........."[: cr.under_alice.level * 3] + cr.under_alice.name)
        .from_("under_alice")
    )

    rows = fetch(query)
    assert [r._asdict()["line"] for r in rows] == [
        "Alice",
        "...Bob",
        "...Cindy",
        "......Dave",
        "......Emma",
        "......Fred",
        "......Gail",
    ]

    next_rows = list(filter(lambda m: "next_rows" in m, caplog.messages))
    assert next_rows == [
        "next_rows = [{'name': 'Bob', 'level': 1}, {'name': 'Cindy', 'level': 1}]",
        "next_rows = [{'name': 'Dave', 'level': 2}, {'name': 'Emma', 'level': 2}, {'name': 'Fred', 'level': 2}, {'name': 'Gail', 'level': 2}]",
        "next_rows = []",
    ]


def test_with_recursive_select():
    """
    See https://www.sqlite.org/lang_with.html

    ..  code-block:: sql

        WITH RECURSIVE
          cnt(x) AS (
             SELECT 1
             UNION ALL
             SELECT x+1 FROM cnt
              LIMIT 1000000
          )
        SELECT x FROM cnt;
    """
    query = (
        With(
            cnt=Select(x=lambda cr: 1).union(
                Select(x=lambda cr: cr.cnt.x + 1).from_("cnt").where(lambda cr: cr.cnt.x < 10)
            )
        )
        .select(x=lambda cr: cr.cnt.x)
        .from_("cnt")
    )
    print(repr(query))
    rows = fetch(query)
    assert [r._asdict()["x"] for r in rows] == list(range(1, 11))


def test_with_select_union(database):
    """
    This is goofy, but, it has a UNION in the WITH target query.
    This UNION is **not** recursive.

    ..  code-block:: SQL

        WITH the_codes(code) as (
            SELECT code FROM names
        )
        SELECT * FROM the_codes
        UNION ALL
        SELECT * FROM the_codes
    """
    values, names, row = database

    query = (
        With(the_codes=Select(code=lambda cr: cr.names.code).from_(names))
        .select(STAR)
        .from_(c="the_codes")
        .union(Select(STAR).from_(c="the_codes"))
    )
    rows = fetch(query)
    assert [r._asdict() for r in rows] == [
        {"code": 1},
        {"code": 2},
        {"code": 3},
        {"code": 1},
        {"code": 2},
        {"code": 3},
    ]


def test_with_clone():
    w1 = (
        With(t2=Values(a=lambda cr: 42).union(Select(a=lambda cr: 3.14).from_("t2")))
        .select(a=lambda cr: cr.t2.a)
        .from_("t2")
    )
    w2 = w1.clone()
    print(w1)
    print(w2)
    results = [r._asdict() for r in fetch(w2)]
    assert results == [{"a": 42}, {"a": 3.14}]
