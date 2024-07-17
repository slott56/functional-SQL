################
Concept
################

..  pull-quote::

    Python's okay, but my mind just seems to work in SQL

That's nice, but that's not a good reason to build temporary SQLite databases full of transient data that's going to be reorganized or summarized.
The cruft of table schemas, bulk inserts, queries, and bulk extracts is a heavy, extraneous burden to permit the use of a ``SELECT`` statement.

SQL is a good way to start the design process.
There's a lot to be said the **Essential SQL Algorithm**.
It's not the best target implementation.

We can leverage SQL thinking to create Python code that avoids SQL database overheads and complications.

An Example
===========

Some SQL

..  code-block:: SQL

    SELECT n.name, v.c2
    FROM names_table n, values_table v
    WHERE n.code = v.c1

Some Python that does the same thing.

..  code-block:: python

    Select(name=lambda cr: cr.n.name, value=lambda cr: cr.v.c2)
    .from_(n=names_table, v=values_table)
    .where(lambda cr: cr.n.code == cr.v.c1)

Yes. The Python is longer. Yes it has ``lambda cr: cr.`` scattered around.
The Python produces the same results as the SQL query, using essentially the same algorithm.

However, It operates directly on native Python data structures.
This means that **all** Python functions and object classes are available.
There's no looking for a SQL equivalent, or -- worse -- a hybrid semi-SQL/semi-Python monstrosity.

The ``lambda`` objects are necessary for building expressions that work on the "composite-row" objects fetched from tables.
We don't want the Python run-time to immediately compute an answer to ``n.code == v.c1``.
We want to provide a version of this expression to be evaluated for each row of the underlying tables.

Since a lambda is a function, **any** one-argument function can be used.
That's a real **any** -- not an *anything you can put into a wrapper or some other hack* -- since this code is native Python.

What's The Point?
=================

The SQL algorithm is a helpful mental model.
Folks who find it easier to think in SQL are leveraging an elegant algorithm that has a number of related design patterns.
The point of this module is not to stop using SQL.
The point is to stop using a database.

What follows is a deep dive into the SQL Algorithm, and some details of SQL features.

Feel free to skip to :ref:`demo` to see a few examples of how this works.

The SQL Algorithm
==================

We'll work with a collection of tables, :math:`T_1` through :math:`T_{n}`.
Each table, :math:`T`, is a set of rows, :math:`T_x = \{ R_1, R_2, \dots, R_{m} \}`.
Each row, :math:`R`, is a collection of atomic values, :math:`R_y = \langle v_1, v_2, \dots \rangle`.

A Query, :math:`Q(T)`, over :math:`n` tables, :math:`T = \{T_1, T_2, \dots, T_{n}\}`, is the following:

..  math::

    Q(T) = H_{C_h(x)} \biggl( G_{K(x); A_p(x), \dots} \Bigl( S_{E_m(x), \dots} \left( W_{C_w(x)} ( F(T) ) \right) \Bigr) \biggr)

There are four higher-order functions, :math:`H_f(T)`, :math:`G_{r;m}(T)`, :math:`S_m(T)`, and :math:`W_f(T)`.
There's one ordinary function :math:`F(T)`.
The higher-order functions are parameterized by other functions.
These are applied to the individual rows of the resulting objects.

This requires rethinking the order of the clauses.
The order ``FROM t WHERE C_w SELECT e_1, e_2, a_1, a_2, ... GROUP BY k HAVING C_h`` reflects the order in which processing occurs.
The algorithm has the following stages:

-   From tables, :math:`T^{*} = F(T)`.

    This joins all the tables. It's a kind of :math:`\prod T`, sometimes stated as :math:`T_0 \bowtie T_1 \bowtie \dots \bowtie T_n`.

-   Where filter, :math:`T^{*^\prime} = W_{C_w(x)}(T^{*})`.

    This applies a condition, :math:`C_w(x)`, to each row in the joined tables, :math:`T^{*}`, to pass rows matching the conditions and meet any other criteria provided. :math:`T^{*^\prime} \subseteq T^{*}`.
    :math:`T^{*^\prime} = \{ r \in T^{*} \mid C_w(r) \}`. In effect, omitting a ``WHERE`` clause makes :math:`C_w(x) = \mathtt{True}`, leading to a cartesian product result.

    A ``JOIN ON`` clause introduces additional logic to :math:`C_w(x)`. In principle, it might imply a sequence of pair-wise joins as the algorithm. While this might be a nice optimization, it doesn't materially alter the processing.
    It is often easier to read than a massive ``WHERE`` clause.

-   Select mapping, :math:`T^{\prime\prime} = S_{E_m(x), \dots}(T^{*^\prime})`.

    This transforms the filtered rows of :math:`T^{*^\prime}` to a new table-like structure by computing values or "projecting" values from the underlying tables. Each :math:`E_m(x)` function maps a composite row's values to a target value. The original table identities are lost at this point.
    :math:`T^{\prime\prime} = \{ r \in T^{*^\prime} \mid \langle E_0(r), \dots, E_m(r) \rangle \}`.

    Note that the :math:`E_m(x)` collection of expressions is a subset of the expressions in the SQL ``SELECT`` clause.
    SQL ``SELECT`` syntax includes  aggregate expressions, :math:`A_p(x)`, even though they're properly part of ``GROUP BY`` processing.

-   Group By reduction, :math:`T^{\Sigma} = G_{K(x); A_p(x), \dots}(T^{\prime\prime})`.

    There are two steps.

    -   First, reduce rows to groups.
        The :math:`K(x)` function maps a row to a group identifier: :math:`\{k \mapsto \{T_k^{\prime\prime}\}\} = G_{K(x)}(T^{\prime\prime})`.
        The mapping function, :math:`K(x)`, has some domain of values, :math:`\mathbb{K}`.
        This domain is the set of all values when :math:`K(x)` is applied to actual rows in :math:`T^{\prime\prime}`.
        Also, the domain can be a vector of values.

        Each value :math:`k \in \mathbb{K}` is associated with a collection of individual rows.
        :math:`\{k \mapsto \{T_k^{\prime\prime}\}\} = \{ k \in \mathbb{K} \mid k \mapsto \{ r \in T^{\prime\prime} \mid K(r) = k \} \}`.

        Absent any explicit group-by, all the data belongs to a single group, and :math:`\mathbb{K} = \{\mathtt{True}\}`.

    -   Second, map groups to aggregate values. While the aggregate functions are specified in the SQL ``SELECT`` clause, they are applied to groups.
        The :math:`A_0(x), \dots, A_p(x)` functions compute aggregated values for the rows in the group.

        Aggregate functions include sum, mean, cout, min, max, etc.
        There are also variants for handling ``NULL`` values.

        The result, :math:`T^{\Sigma}` is a new table, with a row for each value in :math:`\mathbb{K}`.
        :math:`\{k \in \mathbb{K} \mid k + \langle A_0(T_k^{\prime\prime}), \dots, A_p(T_k^{\prime\prime}) \rangle \}`.

        If there are no aggregates, the result is :math:`\mathbb{K}`, the set of values computed by the :math:`K(x)` function.

    -   Important. If there is no ``GROUP BY`` clause and no aggregates, the result is :math:`T^{\Sigma} = T^{\prime\prime}`.
        Since there can be no ``HAVING`` clause without a ``GROUP BY`` clause, with no ``GROUP BY``, processing is effectively finished.

-   Having filter, :math:`T^{\Sigma^\prime} = H_{C_h(x)}(T^{\Sigma})`.

    This applies a condition, :math:`C_h(x)`, to each row in the group-by result to pass matching rows. :math:`T^{\Sigma^\prime} \subseteq T^{\Sigma}`. Absent a ``HAVING`` clause, :math:`C_h(x) = \mathtt{True}`, and all rows are kept. As noted earlier, if there's no ``GROUP BY`` clause, there can be no ``HAVING`` clause.

    This is essentially identical to the Where filter processing, :math:`W_{C_w(x)}(T^{*})`.

Yes, the order these functions are applied is not the order ``SELECT`` statements are commonly written.


We can think of this as a composite function that's closer to ``SELECT`` syntax.

..  math::

    Q(T) = (S_{E_m(x), \dots; A_p(x), \dots} \circ F \circ W_{C_w(x)} \circ G_{K(x), \dots} \circ H_{C_h(x)})(T)

It's similar to the more commonly-used order of clauses.

What's important are these features:

1.  The sequence of operations is based on higher-order functions ``filter()``, ``map()`` ``reduce()``, and one ordinary ``product()`` function.

2.  The sequence applies to "composite" rows from a number of tables prior to the ``SELECT`` and new rows from a single table after the ``SELECT``.

3.  All SQL expressions are functions that apply to rows of a table. In the case of the ``SELECT`` expressions that are scalar, and the ``WHERE`` expression, the "row" is a composite object from the :math:`T^{*}` interim result. In the case of the aggregate ``SELECT`` epxressions and the ``HAVING`` expression, the row is a simple row of values.

Here's the way higher-order functions apply to SQL clauses:

..  csv-table::
    :header: Clause, Function

    ``FROM``,itertools.product()
    ``WHERE``,filter() using :math:`C_w(x)`.
    ``SELECT``,map() applied for each :math:`E_m(x)`.
    ``GROUP BY``,reduce() and map() applied for each :math:`A_p(x)`.
    ``HAVING``,filter() using :math:`C_h(x)`.

The Group By Alternatives
=========================

There are four cases for ``GROUP BY`` and aggregate functins in the ``SELECT`` clause:

-   No ``GROUP BY``, no aggregates in ``SELECT``. The results of :math:`(S \circ W \circ F)(T)` are complete.

-   No ``GROUP BY``, one or more aggregates in ``SELECT``. The result is a single summary row.
    It's :math:`(G \circ S \circ W \circ F)(T)`, but the group-by operation is a kind of degenrate case;
    it creates a single group.
    There can be no ``HAVING`` without a ``GROUP BY``.

-   A ``GROUP BY`` clause, and aggregates in ``SELECT``.
    The result is a new table of summary rows, :math:`(G \circ S \circ W \circ F)(T)` which can then be processed by the ``HAVING`` clause.

-   A ``GROUP BY`` clause, but no aggregates in ``SELECT``. Not sure what this means.
    SQLite appears to ignore the ``GROUP BY`` and produce all rows.
    It seems also sensible to report the group keys and be done with it.

The ``GROUP BY`` expression needs to be computed for each query composite row.
Consequently, a ``.group_by(name=lambda...)`` creates a new ``name=lambda...`` in the ``Select`` clause.

The Subqueries and the Exists Function
=======================================

A subquery can appear in a number of places:

-   ``FROM``
-   ``SELECT``
-   ``WHERE``
-   ``HAVING``


See https://www.w3resource.com/sql/subqueries/understanding-sql-subqueries.php for examples.

For the ``FROM`` clause, the subquery provies a table. This is consistent with the definition of :math:`Q(T)` above.

For the other clauses, there are three kinds of results: a set of values, a single value, or a boolean.

-   The subquery produces a set of values used for collection operators like ``IN`` or ``NOT IN``.
    This suggests a value selector function can pick values from a single column of the result, :math:`V_c(Q(T))` will
    pick one column, :math:`c` from all rows, :math:`V_c(Q(T)) = \{r \in Q(T) \mid r_c\}`, to create a set of values.

-   The subquery produces a single value for scalar operators.
    This suggests a wrapper function to pick one row from the result and then pick one value from the row.
    The resulting table has one or more rows, :math:`T^{\Sigma^\prime} = \{R_1, R_2, \dots, R_n\}`.
    The first row has one or more values, :math:`R_1 = \langle v_1, v_2, \dots, v_n \rangle`.
    The value selector function, :math:`V_{n, c}(Q(T)) = {Q(T)_n}_c`, can pick row :math:`n`, and column :math:`c` of the table to retrieve the scalar value.

-   In an ``EXISTS()`` context the subquery producing any result at all means ``EXISTS()`` is ``True``.
    Failing to produce a result means  ``EXISTS()`` is ``False``. A function, :math:`\exists(Q(T))` is applied to see if there was a row.

These wrapper functions to get all values from a columns or a specific value from a row and a column are implicit in SQL.
The ``EXISTS()`` function is the only one that's explicit.
The implicit value-extraction is a handy assumption that simplifies SQL slightly.

There are two subquery contexts:

-   Independent. In this case, the subquery has no expressions that reference tables from the parent query.
    The subquery must be executed first, and the resulting value provided to the parent query.

-   Bound. In this case, the subquery has one or more expressions that reference tables from the parent query.
    This means the :math:`Q(T)` function requires a second argument value: :math:`Q(T; R)`, where :math:`R` is the current row in the query that contains the subquery.
    This also means any of the functions :math:`E_m(x)`, :math:`C_w(x)`, or :math:`C_h(x)` may include the results of a subquery.
    For example, :math:`E_m(x) = V_{1,1}(Q_b(T; x))`, describes a scalar result of a bound subquery, :math:`Q_b`, found in the ``SELECT`` clause expression, :math:`E_m(x)`.
    One commonly-used function for the ``WHERE`` and ``HAVING`` clauses is the exists test, :math:`\exists(Q(T; R)`).
    It may also be a function to a value by executing the subquery, :math:`V_{1,1}(Q(T; R))`.

The bound subquery is also implicit in SQL.
This, too, is a handy assumption that simplifies SQL slightly.

What's essential here is the subquery processing has very handy implicit behavior.


Common Table Expressions
========================

A **Common Table Expression** (**CTE**) has a creation query, :math:`Q_w`, prior to a target query.
These are specified in a ``WITH`` clause, prior to the target select.
The creation query prepares a table-like structure that can be incorporated into another query.

..  math::

    Q(T, T_w = Q_w(T))

There can be more than one of these creation queries to create tables for use in the target query.

Additionally, the creation query can involve recursion.

..  math::

    Q_w(T) = \begin{cases}
        T_w &= Q_{w0}(T)  \text{ initially},\\
        T_w &= Q_{wu}(T, T_w)  \text{ if $T_w \neq \emptyset$},\\
    \end{cases}

Often, the initialization, :math:`Q_{w0}`, is a ``VALUES`` clause.
The recursion, :math:`Q_{wu}`, is specified as a ``UNION`` or ``UNION ALL`` clause that's syntactically part of the initial ``VALUES`` clause.
The choice between breadth-first and depth-first traversal of the query results is specified with an ``ORDER BY`` clause.
The default is breadth-first.

Other Query Features
====================

Some "other" features of SQL queries include the following:

-   Order BY. This is best handled by Python's native :py:func:`sorted` function.
    ``sorted(fetch(Q), key=lambda row: ...)``.

-   Limit. This is best handled by Python's native list slicing.
    ``data = list(fetch(Q))[start:stop]``.

-   Union, Intersect, Except. There are set operations that are part of Python.
    The complication here is that the underlying :py:class:`sqlful.Row` objects are mutable dictionaries.
    To do set operations, it's best to make immtutable, frozen dataclasses.

These can all be done with relative ease.
There isn't any SQL-like syntax for these features.
