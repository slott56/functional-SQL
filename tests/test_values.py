"""
Test ``VALUES`` statement.
"""

from funcsql import *


def test_values():
    values = Values(name=lambda cr: "Life", value=lambda cr: 42.0)
    expected = [
        {
            "name": "Life",
            "value": 42.0,
        },
    ]
    assert expected == [row._asdict() for row in fetch(values)]

    assert expected == [row._asdict() for row in list(values)]


def test_values_clone():
    v1 = Values(name=lambda cr: "a").union(Select(name=lambda cr: "b"))
    v2 = v1.clone()
    results = [r._asdict() for r in fetch(v2)]
    # Why only one row?
    # The fetch_with() handles the Values().union() case separately
    assert results == [{"name": "a"}]
