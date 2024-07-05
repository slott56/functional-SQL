..  _`funcsql`:

############
funcsql Code
############

Here's the content of the :py:mod:`funcsql` module.

..  uml::

    @startuml

    package funcsql {

        class Table
        class Row

        Table *- Row : produces

        class QueryComposite

        QueryComposite *-- Row

        class Select {
            from_()
            where()
            join()
            group_by()
            having()
        }

        class Aggregate
        class SelectStar
        class lambda << (F,orchid) >>

        Select o-- Aggregate
        Select - SelectStar
        Select o-- lambda

        class fetch << (F,orchid) >>

        fetch --- Select : executes
        fetch o--> Row : > produces
        fetch o-- Table : < consumes
        fetch o-- QueryComposite : uses

    }

We'll look at the :py:class:`funcsql.Table` and :py:class:`funcsql.Row` structures first.
Then the :py:class:`funcsql.Select` class, used to define a query.

The :py:func:`funcsql.fetch` function embodies the **Essential SQL Algorithm**.
It executes the query object, consuming rows from tables and producing rows in a result.
Along the way, it builds :py:class:`funcsql.QueryComposite` objects which are provided to lambdas to evaluate expressions.

Table and Row
=============

The :py:class:`funcsql.Table` objects contain the data to be processed.
The :py:class:`funcsql.Row` is a wrapper that provides handy attribute name access for dictionary keys.

Table
-----

..  autoclass:: funcsql.Table
    :members:

Row
---

..  autoclass:: funcsql.Row
    :members:
    :private-members:

Select query builder
====================

The :py:class:`funcsql.Select` class is used by build queries (and subqueries.)
It's used by the :py:func:`funcsql.fetch` function (among others) to consume rules from :py:class:`funcsql.Table` objects
and produce an iterable sequence of :py:class:`funcsql.Row` results.

The result of a :py:class:`funcsql.Select` construction is a data structure to be used by the :py:func:`funcsql.fetch` function.
A :py:class:`funcsql.Select` is iterable as a convenience.

Select
------

..  autoclass:: funcsql.Select
    :members:

SelectStar
----------

..  autoclass:: funcsql.SelectStar

There's one instance of this class, called ``STAR``.

Aggregate
----------

Aggregate comptuations are done **after** grouping, and must be delayed until then.
To make this work out, they're wrapped as an object that's distinct from a simple ``lambda``.

..  autoclass:: funcsql.Aggregate
    :members:

QueryComposite
--------------

These objects move through the :py:func:`funcsql.fetch` function's pipeline of steps.

..  autoclass:: funcsql.QueryComposite
    :members:

SQL Algorithm
==============

fetch
-----

..  autofunction:: funcsql.fetch

..  autofunction:: funcsql.exists

fetch values
------------

..  autofunction:: funcsql.fetch_first_value

..  autofunction:: funcsql.fetch_all_values

component functions
--------------------

..  autofunction:: funcsql.from_product
..  autofunction:: funcsql.where_filter
..  autofunction:: funcsql.select_map
..  autofunction:: funcsql.aggregate_map
..  autofunction:: funcsql.group_reduce
..  autofunction:: funcsql.having_filter

Other SQL
=========

These perform the expected operation on the underlying :py:class:`funcsql.Table`.
It's often better to reach into the ``Table`` directly.
The point of the :py:class:`funcsql.Table` class is to wrap an underlying Python data structure.


..  autoclass:: funcsql.Insert

..  autoclass:: funcsql.Update

..  autoclass:: funcsql.Delete
