.. _Tutorial:

#########
Tutorial
#########

There are several parts to this tutorial:

1.  `Queries`_

2.  `Schema and Tables`_

3.  `WITH clause and Recursion`_

A more complete example is in :ref:`demo`.

Queries
=======

The essential SQL query has a number of clauses.
Here's a short example of a ``SELECT``:

..  code-block:: SQL

    SELECT n.name, v.c2
    FROM names_table n, values_table v
    WHERE n.code = v.c1

We rewrite this into a Python :py:class:`funcsql.Select` object.
Each clause has unique rewrite rules, depending con what the SQL clause does.

1.  ``SELECT``. Each variable or expression must becomes a lambda object, to be computed later.
    A target variable must be provided; this is in effect, a mandatory ``AS`` clause.

    ..  code-block:: Python

        Select(name=lambda cr: cr.n.name, value=lambda cr: cr.v.c2)

    The ``cr`` parameter is a reminder that the lambda will be evaluated with a "composite row".
    This row has the tables named in the from clause and the columns of those tables.
    The ``cr.n.name`` expression picks the table named ``n`` and the column ``name`` from that table.

2.  ``FROM``. Each table name is replaced by a ``Table`` object. We'll see how these are made in the `Schema and Tables`_ section.

    ..  code-block:: Python

        .from_(n=names_table, v=values_table)

    As with the ``SELECT`` clause, this provides the alias name and the table name.
    Table names can be listed without alias names, also.
    The tables must be loaded *before* building the query.

3.  ``WHERE``. The logical condition becomes a lambda, also.

    ..  code-block:: Python

        .where(lambda cr: cr.n.code == cr.v.c1)

The ``.from_()`` and ``.where()`` syntax are methods to add details to the :py:class:`funcsql.Select` object.
There are other methods include ``.group_by()`` and ``.having()``.

Generally, the whole thing must either be complete on one line, or wrapped in ``()``\ 's.
This seems best:

::

    from funcsql import *

    query = (
        Select(name=lambda cr: cr.n.name, value=lambda cr: cr.v.c2)
        .from_(n=names_table, v=values_table)
        .where(lambda cr: cr.n.code == cr.v.c1)
    )

Using wrapping ``()``\ 's makes the query object easier to work with.

We call the :py:class:`funcsql.Select` a "Query Builder".
It doesn't "do" anything.
It barely has any internal state changes.
It collects the various clauses an options of a query.

A separate :py:func:`funcsql.fetch` function uses a query object to process data defined in :py:class:`funcsql.Table` objects.

Schema and Tables
==================

A :py:class:`funcsql.Table` object has a name and a list of rows.
The list of rows need to be dictionary objects.
The keys of this dictionary are the column names.

We limit column names to valid Python identifiers.
After all, this is pure Python code.
Python identifiers, for example, are case sensitive, where in SQL, there's no such rule.

How this data arrives on the scene is left wide open.
For one example, consider a CSV-format file with a bunch of columns.

::

    from csv import DictReader
    from pathlib import Path
    from funcsql import *

    table_1_path = Path("table_1.csv")
    with open(table_1_path) as source_file:
        rdr = DictReader(source_file)
        table_1 = Table("table_1", list(rdr))

There's no formal SQL-schema with table definitions.
The table is defined by the column names.
The column names in the CSV file need to match the column names in the ``query`` object.

That's the only rule:

..  important::

    Any source of ``list[dict[str, Any]]`` data can build a :py:class:`funcsql.Table` object.

Also important, the :py:class:`funcsql.Row` objects will be created for you as needed.
Do not map source data to :py:class:`funcsql.Row` instances.

Here are two other examples of tables:

::

    from funcsql import *

    values_table = Table(
        "values_table",
        [
            {"c1": 1, "c2": 42.0},
            {"c1": 2, "c2": 3.14},
            {"c1": 3, "c2": 2.72},
        ],
    )
    names_table = Table(
        "names_table",
        [
            {"code": 1, "name": "Life"},
            {"code": 2, "name": "Pi"},
            {"code": 3, "name": "Ee"},
        ],
    )

And, yes, the table name matches the variable name to which the :py:class:`funcsql.Table` object is assigned.
This isn't a requirement, but debugging can be a nightmare if the variable names don't match the table names.

Fetching Rows
=============

To actually execute the query, use the :py:func:`funcsql.fetch` function.

1. Load the tables, assigning them to variables.
2. Build the query with references to the table variables. Assign this to a variable.
3. Apply the :py:func:`funcsql.fetch` function the query. This is an iterable that returns :py:func:`funcsql.Row` objects.

The idea is to be able to to SQL-like processing with minimal overhead.

The result is a sequence of :py:class:`funcsql.Row` objects.
These are similar to named tuples.
The attribute names come from the :py:class:`funcsql.Select` instance, which has parameters of the form ``name=lambda cr:...``.

::

    from funcsql import *

    names_table = Table("names_table", ...)
    values_tables = Table("values_table", ...)
    query = (Select...)

    for row in fetch(query):
        print(row)

The idea is the minimize the overheads.
This doesn't have a database connection.
It doesn't have any cursor management or locking or commits.
It doesn't create or require a SQL schema.
It does SQL-like processing on Table-like objects.

Group By and Having
===================

Here's an example of a ``GROUP BY`` clause:

..  code-block:: SQL

    SELECT group AS key, sum(value) AS total
    FROM raw_table
    GROUP BY key

Here's the rewrite to use the :py:meth:`funcsql.Select.group_by` method to build the grouping.
This also uses a :py:class:`funcsql.Aggregate` object that wraps a function, the built-in :py:func:`sum`,
and a lambda to compute the parameter values for this function.

The ``value`` item, specifically, is used to extract the required column from the composite row.

::

    from funcsql import *

    query = (
        Select(
            key=lambda c: c.raw.group,
            value=lambda c: c.raw.value,
            total=Aggregate(sum, "value")
        )
        .from_(raw_table)
        .group_by("key")
    )

This has a strange-looking redundancy.
The ``value=lambda`` creates a value for the ``total=Aggregate``.
This can be abbreviated to ``Aggregate(sum, value=lambda c: c.raw.value)``.

When parsing SQL, a database engine will make a number of optimizations when working out what a name might refer to.
In contrast, this library works directly in Python; it doesn't have access to the original variable names, table schema,
or expressions.

Here's the table used for the above query.

::

    from funcsql import *

    raw_table = Table(
        "raw_table",
        [
            {"group": "1", "value": 1},
            {"group": "1", "value": 1},
            {"group": "2", "value": 2},
            {"group": "2", "value": 3},
        ],
    )

Subqueries
==========

Here's an example of a subquery:

..  code-block:: SQL

    SELECT first_name
    FROM employees
    WHERE department_id IN (
        SELECT department_id FROM departments WHERE location_id>1500
    );

Part of the query is the ``department_id`` set created by the subquery.

Here's an alternative formulation as pure Python.

::

    from funcsql import *

    department_ids = set(
        fetch_all_values(
            Select(department_id=lambda c: c.departments.department_id)
            .from_(departments)
            .where(lambda c: int(c.departments.location_id) > 1500)
        )
    )

    c3 = (
        Select(first_name=lambda c: c.employees.first_name)
        .from_(employees)
        .where(lambda c: c.employees.department_id in department_ids)
    )

Note there are two queries.
This reflects the meaning of the SQL, as well as the syntax.
The queries aren't syntactically nested.

First, the subquery ``SELECT department_id FROM departments ...`` is executed to create a set of ids.
Second, the main query executes, using that set of ids.

It's possible to combine them into a single construct.
This is -- after all -- pure Python.
The ``set(...)`` expression that computes the value of ``department_ids`` can replace the ``department_ids`` variable in the ``lambda c: c.employees.department_id in department_ids`` expression.
The lambda becomes very long, but, the subquery is textually part of the main query, if that's important for reader comprehension.

In principle, a SQL database might optimize ``IN (SELECT x...)`` to a one-row lookup using an index or something.
Since the Python set does lookups so quickly, it's often faster to build the set of values, then do set membership tests.

The Exists Clause
=================

The SQL ``EXISTS()`` function generally contains a subquery that includes a reference to the containing query.

For example,

..  code-block::

    SELECT e.last_name
    FROM employees e
    WHERE EXISTS (
        SELECT * FROM employees b
        WHERE b.employee_id = e.manager_id AND b.last_name = 'King'
    )

The subquery uses ``e.manager_id`` to refer to a column in a row in the containing query.
Here's the rewritten query.

::

    from funcsql import *

    c5 = (
        Select(last_name=lambda c: c.e.last_name)
        .from_(e=employees)
        .where(
            lambda c: exists(
                c,
                Select(STAR)
                .from_(b=employees)
                .where(lambda sq: sq.b.employee_id == sq.e.manager_id and sq.b.last_name == "King"),
            )
        )
    )

An ``exists()`` function has two parameters:

-   The context; the composite row from the parent query.

-   A Query, usually a :py:class:`funcsql.Select` object.

Using the given context, the query is evaluated.
All of the tables from the parent query are available in the child query.
Table aliases are absolutely required to disambiguate references.

``WITH`` clause and Recursion
================================

We have two choices for creating "common table expressions":

-   Just like everything else -- the `With is a QueryBuilder`_ implementation.

-   `The Python with statement`_ implementation.
    This comes close to the SQL ``WITH`` clause, but doesn't do everything.

With is a QueryBuilder
~~~~~~~~~~~~~~~~~~~~~~

Here's a simple example:
::

    (
        With(
            table_1=Select(...),
            table_2=Select(...)
        )
        .query(Select(...).from_("table_1", "table_2"))
    )

The :py:class:`funcsql.With` uses ``table_name = Select`` to match the SQL ``table_name AS (SELECT...)``.

The :py:meth:`funcsql.With.query` method expects a :py:class:`funcsql.Select` object.
The table names are strings, since the tables aren't part of the global namespace; they're part of the context of the :py:class:`funcsql.With` object.

We can also write this as follows:

::

    (
        With(
            table_1=Select(...),
            table_2=Select(...)
        )
        .select(...).from_("table_1", "table_2"))
    )

The use of the :py:meth:`funcsql.With.select` method more closely parallels the SQL syntax.
Use either the :py:meth:`funcsql.With.query` method with an separate :py:class:`funcsql.Select`,
or use the :py:meth:`funcsql.With.select` method.
Don't use both, and don't mix-and-match in your application.

The Python ``with`` statement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following is really unpleasant, but works:

::

    from contextlib import nullcontext
    from funcsql import *

    with nullcontext(
        fetch_table("the_codes", Select(code=lambda cr: cr.names.code).from_(names))
    ) as the_codes:
        rows = fetch(Select(STAR).from_(the_codes))

The complication is a :py:class:`funcsql.Table` has an internal name, separate from the variable name.
Ideally, they match.

This is more pleasant:

::

    from funcsql import *

    with fetch_table("the_codes", Select(code=lambda cr: cr.names.code).from_(names)) as the_codes:
        rows = fetch(Select(STAR).from_(the_codes))

This works because a ``Table`` is a context manager that does almost nothing.

This doesn't help specify recursive queries, since they're actually part of the ``WITH`` clause that creates the CTE used by the target query.

More on recursive query building
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The examples in https://www.sqlite.org/lang_with.html are particularly good at showing the recursive query technique.

..  code-block:: SQL

    WITH RECURSIVE
      works_for_alice(n) AS (
        VALUES('Alice')
        UNION
        SELECT name FROM org, works_for_alice
         WHERE org.boss=works_for_alice.n
      )
    SELECT avg(height) FROM org
     WHERE org.name IN works_for_alice;

Is restated as follows:

..  code-block:: Python

    from funcsql import *

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

Note the :py:class:`funcsql.Values` object,
which implements the SQL ``Values`` clause.
The SQL ``UNION`` becomes a :py:meth:`funcsql.Values.union` method in query construction.

A ``Select()...union(Select()...)`` **outside** the ``WITH`` context is an ordinary Union.
It's the same as ``+`` operator between the
data lists that make up a Table.

In a ``With(table=Select()...union(Select().from("table")...))`` **inside** a ``WITH`` context, the
union specifies recursive traverssal.
Note that this also uses string table name instead of a :py:class:`funcsql.Table` object.
The ``"under_alice"`` table is the whole point being of this Common Table Expression.
The recursive query is building this table. It doesn't really exist until after the recursive query is complete.
