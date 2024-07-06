#########
Notes
#########

Some Features
=============

1. ``WITH`` clause and Recursion
2. The Values clause
#. Partitioned Tables

``WITH`` clause and Recursion
-----------------------------

This is interesting, and requires a recursive fetch function.
An initial ``SELECT`` or ``VALUES`` seeds a FIFO queue.
While the queue is not empty, the first item is yielded as a result and also becomes the context for a bound subquery that appends to the queue.

There are a number of changes. First, there are two new query builders to support this:

-   ``Values`` subclass of the Query Builder to create a degenerate query-like structure to emit literal values.
    The point is merely to pass the values through to the :py:func:`funcsql.fetch` function.
    The values are expressions. Which means there can be a subquery involved.

-   ``With`` subclass of Query Builder.

    -   Variant 1 is ``With(table_name, as=Select(...), union=Select(...)).query(Select(...))``. These are recursive. (Note ``union`` vs. ``union_all``.)
        This can also be ``With(table_name, as=Values(...), union=Select(...)).query(Select(...))``

    -   Variant 2 is ``With(table_name, as=Select(...)).query(Select(...))``.
        These can be "chained": ``With(table_name, as=Select(...)).with(table_name, as=Select(...)).query(Select(...))``.
        Note the ``with()`` method with the same parameters as ``With.__init__()``.

        These are essentially ``table_name = fetch(Select)``.
        What's interesting is the scope question: the tables only last for the duration of the ``fetch()`` executing
        the ``With``.

This leads to several distinct variants of :py:func:`funcsql.fetch`:

-   ``fetch(Select()...)``.

-   ``fetch(Values())``. A special case used by the recursive ``With`` to simply produce values.

-   ``fetch(With(table_name, as=Select(...), union=Select(...).query(Select(...))`` with recursion. The ``from_`` or ``join`` in the ``Select`` must reference the CTE in the ``With``.
    See https://www.sqlite.org/lang_with.html for notes on the breadth-first traversal of the recursive results.

-   ``fetch(With(table_name, as=Select(...).query(Select(...))``.  The non-recursive version (without the ``union=``).
    In principle, this is a degenerate case where -- absent the ``union`` clause -- nothing is put into the queue and it's "one-and-done."

This seems to be a straight-forward overloaded function with three parameter types.
While Python doesn't have Julia-style overloading, a wrapper ``fetch()`` can single-dispatch to the implementation ``fetch()`` functions.
See https://docs.python.org/3/library/functools.html#functools.singledispatch.

While it seems like a ``QueryBuilder`` superclass might be helpful to unify the ``Select``, ``Values``, and ``With`` subclasses, they have little in common.
At most, they're all support ``__iter__()`` as  ``Iterator[Row]``.
The alternative is ``type QueryBuilder = Union[Select, Values, With]``.

Values clause
-------------

The ``Values()`` builder can **also** be used by the ``INSERT`` implementation.
It would unify ``INSERT INTO table SELECT...`` and ``INSERT INTO table VALUES``.
It would be ugly, though.

::

    Insert().into(table).values([{data}])

vs.

::

    Insert().into(table).values(Values({data}))

vs.

::

    Insert().into(table).values(Select(...))

The point is to minimize the reliance on SQL tables.
These become elaborate wrappers around lists or partitioned sequences of lists.

Partitioned Tables
------------------

These should be an extention to :py:class:`funcsql.Table` and nothing more.
The use of :py:func:`list` in :py:func:`funcsql.group_reduce` is a potential problem.

1. Fix :py:class:`funcsql.Table` to replace :py:func:`list`.

2. Fix :py:func:`funcsql.group_reduce` to use :py:class:`funcsql.Table` instead of :py:func:`list`.

3. Subclass :py:class:`funcsql.Table` to show how partitioning would work.


To Do's
==========

..  todolist::

