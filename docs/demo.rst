..  _demo:

###################
Demonstration Code
###################

Example 1
=========

Some imports

..  literalinclude:: ../tests/demo_1.py
    :lines: 11-15

Read the raw data file.
This function simply returns the list of dictionaries from the ``csv.DictReader``.
The columns aren't useful as shown.

..  literalinclude:: ../tests/demo_1.py
    :lines: 18-30

The column names are x123, y1, y2, y3, x4, and y4, which require restructuring.

We want a table like the following:

..  uml::

    @startuml
    hide methods
    hide circle

    class Anscombe {
        series: int
        x: float
        y: float
    }
    @enduml

There are four series, each use a subset of columns:

- {series: 1, x: x123, y: y1}

- {series: 2, x: x123, y: y2}

- {series: 3, x: x123, y: y3}

- {series: 4, x: x4, y: y4}

One way to restructure this is a ``UNION`` of four queries.

..  code-block:: SQL

    SELECT 1, x123 as x, y1 as y
    FROM raw
    UNION
    SELECT 2, x123 as x, y2 as y
    FROM raw
    UNION
    SELECT 3, x123 as x, y3 as y
    FROM raw
    UNION
    SELECT 4, x4 as x, y4 as y
    FROM raw

We can do this as follows without the overhead of creating and loading one table
that we'll used to create a second table.

..  literalinclude:: ../tests/demo_1.py
    :lines: 33-66

The real goal is to compute some descriptive statistics after restructuring the data.

..  code-block:: SQL

    SELECT series, MEAN(x), MEAN(y)
    FROM anscombe
    GROUP BY series

The query is a bit longer, but (again) doesn't involve the overhead of loading table.
Or -- in this example -- loading one table with raw data and then inserting into
another table to restructure the data.

We've highlighted the :py:class:`funcsql.Select` that corresponds to the statistics query.

..  literalinclude:: ../tests/demo_1.py
    :lines: 71-94
    :emphasize-lines: 16-21

This does the same processing without the conceptual overheads of table schema,
or other SQL complications like connections and commits.

Example 2
=========

TBD
