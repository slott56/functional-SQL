"""
Spike for the functional decomposition of breadth-first recursion.

See https://www.sqlite.org/lang_with.html

::
    
    CREATE TABLE org(
      name TEXT PRIMARY KEY,
      boss TEXT REFERENCES org
    ) WITHOUT ROWID;
    Organization(name='Alice',NULL);
    Organization(name='Bob','Alice');
    Organization(name='Cindy','Alice');
    Organization(name='Dave','Bob');
    Organization(name='Emma','Bob');
    Organization(name='Fred','Cindy');
    Organization(name='Gail','Cindy');

Depth First::

    Alice
    ...Bob
    ......Dave
    ......Emma
    ...Cindy
    ......Fred
    ......Gail

Breadth First::

    Alice
    ...Bob
    ...Cindy
    ......Dave
    ......Emma
    ......Fred
    ......Gail


"""

from dataclasses import dataclass
from typing import Iterable, Iterator

@dataclass
class Organization:
    name: str
    boss: str | None

org = [
    Organization(name='Alice', boss=None),
    Organization(name='Bob', boss='Alice'),
    Organization(name='Cindy', boss='Alice'),
    Organization(name='Dave', boss='Bob'),
    Organization(name='Emma', boss='Bob'),
    Organization(name='Fred', boss='Cindy'),
    Organization(name='Gail', boss='Cindy'),
]

@dataclass
class UnderAlice:
    name: str
    level: int


def depth_first(seed: list[UnderAlice]) -> Iterator[Organization]:
    """If the query has ORDER BY (DESC) in it..."""
    # Result
    yield from seed
    # fetch() next from seed
    has_boss = [
        UnderAlice(person.name, s.level + 1)
        for s in seed
        for person in filter(lambda org: org.boss == s.name, org)
    ]
    # Navigate to individual next items.
    if not has_boss:
        return
    for person in has_boss:
        yield from depth_first([person])

def breadth_first(seed: list[UnderAlice]) -> Iterator[Organization]:
    # Result
    yield from seed
    # fetch() next from seed
    has_boss = [
        UnderAlice(person.name, s.level + 1)
        for s in seed
        for person in filter(lambda org: org.boss == s.name, org)
    ]
    # Navigate to *all* next items.
    if not has_boss:
        return
    yield from breadth_first(has_boss)

if __name__ == "__main__":
    print("Depth First")
    seed = UnderAlice('Alice', 0)
    for under_alice in (depth_first([seed])):
        print(f"{(under_alice.level*3)*'.'}{under_alice.name}")

    print("Breadth First")
    seed = UnderAlice('Alice', 0)
    for under_alice in (breadth_first([seed])):
        print(f"{(under_alice.level*3)*'.'}{under_alice.name}")

