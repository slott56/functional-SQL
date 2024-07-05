"""
Test Data Manipulation Language (DML) capabilities:

-   Insert
-   Update
-   Delete
"""

import pytest

from funcsql import *


@pytest.fixture()
def database():
    values = Table(
        "values",
        [
            {"c1": 1, "c2": 42.0},
            {"c1": 2, "c2": 3.14},
            {"c1": 3, "c2": 2.72},
        ],
    )
    names = Table(
        "names",
        [
            {"code": 1, "name": "Life"},
            {"code": 2, "name": "Pi"},
            {"code": 3, "name": "Ee"},
        ],
    )
    return values, names


def test_insert(database):
    values, names = database

    ins_1 = Insert().into(values).values([{"c1": 4, "c2": 6.28}])
    ins_1()
    ins_2 = Insert().into(names).values([{"code": 4, "name": "Phi"}])
    ins_2()

    v_cursor = Select(STAR).from_(values)
    v_rows = [row._asdict() for row in fetch(v_cursor)]
    assert v_rows == [
        {"c1": 1, "c2": 42.0},
        {"c1": 2, "c2": 3.14},
        {"c1": 3, "c2": 2.72},
        {"c1": 4, "c2": 6.28},
    ]

    n_cursor = Select(STAR).from_(names)
    n_rows = [row._asdict() for row in fetch(n_cursor)]
    assert n_rows == [
        {"code": 1, "name": "Life"},
        {"code": 2, "name": "Pi"},
        {"code": 3, "name": "Ee"},
        {"code": 4, "name": "Phi"},
    ]


def test_update(database):
    values, names = database

    upd_1 = Update(names).set(name=lambda row: "Frank").where(lambda row: row.name == "Ee")
    upd_1()

    n_cursor = Select(STAR).from_(names)
    n_rows = [row._asdict() for row in fetch(n_cursor)]
    assert n_rows == [
        {"code": 1, "name": "Life"},
        {"code": 2, "name": "Pi"},
        {"code": 3, "name": "Frank"},
    ]


def test_delete(database):
    values, names = database

    del_1 = Delete().from_(names).where(lambda row: row.name == "Pi")
    del_1()

    n_cursor = Select(STAR).from_(names)
    n_rows = [row._asdict() for row in fetch(n_cursor)]
    assert n_rows == [
        {"code": 1, "name": "Life"},
        {"code": 3, "name": "Ee"},
    ]
