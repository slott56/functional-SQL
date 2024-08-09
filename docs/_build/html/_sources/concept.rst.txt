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
Each table, :math:`T`, is a set of rows, :math:`T_x = \{ r_1, r_2, \dots, r_{m} \}`.
Each row, :math:`r`, is a tuple of atomic values, :math:`r = \langle v_1, v_2, \dots \rangle`.

A Query, :math:`Q(T)`, over :math:`n` tables, :math:`T = \{T_1, T_2, \dots, T_{n}\}`, is the following:

..  math::

    Q(T) = H_{C_h(r)} \biggl( G_{K(r); A_p(R_k), \dots} \Bigl( S_{E_m(r), \dots} \left( W_{C_w(x)} ( F(T) ) \right) \Bigr) \biggr)

There are four higher-order functions, :math:`H_f(R)`, :math:`G_{r;m}(T)`, :math:`S_m(T)`, and :math:`W_f(T)`.
There's one ordinary function :math:`F(T)`.
The higher-order functions are parameterized by other functions.
These parameter functions are applied to the individual rows of table collections.

This requires rethinking the order of the clauses.
The order ``FROM t WHERE C_w SELECT e_1, e_2, a_1, a_2, ... GROUP BY k HAVING C_h`` reflects the order in which processing occurs.
The algorithm has the following stages:

-   From tables, :math:`T^{*} = F(T)`.

    This joins all the tables. It's a kind of :math:`\prod T`, sometimes stated as :math:`T_1 \bowtie T_2 \bowtie \dots \bowtie T_n`.

-   Where filter, :math:`T^{*^\prime} = W_{C_w(x)}(T^{*})`.

    This applies a condition, :math:`C_w(x)`, to each row in the joined tables, :math:`x \in T^{*}`, to pass rows matching the condition, creating a subset, :math:`T^{*^\prime} \subseteq T^{*}`.
    :math:`T^{*^\prime} = \{ r \in T^{*} \mid C_w(r) \}`. In effect, omitting a ``WHERE`` clause makes :math:`C_w(x) = \mathtt{True}`, leading to a cartesian product result.

    A ``JOIN ON`` clause introduces additional logic to :math:`C_w(x)`. In principle, it might imply a sequence of pair-wise joins as the algorithm. While this might be a nice optimization, it doesn't materially alter the processing.
    It is often easier to read than a massive ``WHERE`` clause.

-   Select mapping, :math:`R = S_{E_m(r), \dots}(T^{*^\prime})`.

    This transforms the filtered rows of :math:`T^{*^\prime}` to a new table structure, :math:`R`, by computing values or "projecting" values from the source tables. Each :math:`E_m(r)` function maps a composite row of values to a single target value. The original table identities are lost at this point.
    :math:`R = \{ r \in T^{*^\prime} \mid \langle E_0(r), \dots, E_m(r) \rangle \}`.

    Note that the :math:`E_m(r)` collection of expressions is a subset of the expressions in the SQL ``SELECT`` clause.
    SQL ``SELECT`` syntax includes  aggregate expressions, :math:`A_p(g)`, even though they're properly part of ``GROUP BY`` processing.

    Each expression, :math:`E_m(r)`, is a lambda, :math:`\lambda r.E_m(r)`.

-   Group By reduction to sub-tables distinguished by key, :math:`K(x)`, :math:`R_{K(x)} = G_{K(x); A_p(x), \dots}(R)`.

    There are two steps.

    -   First, decompose the original table, :math:`R`, into sub-tables, :math:`R_k`, with a common key value, :math:`k`.
        The given :math:`K(x)` function maps each row to a common key value.
        This function has some universe of values over the rows in R: :math:`\mathbb{K} = \{K(r) \mid r \in R\}`.
        (To support complex keys, the value of :math:`k` can be a tuple of atomic values.)

        Each value, :math:`k \in \mathbb{K}`, is associated with a sub-table of rows.
        :math:`k \mapsto \{R_k\}`, or, :math:`R_k = \{ r \in R \mid K(r) = k \}`.

        Absent any explicit group-by clause, all the data belongs to a single group, and the universe of values is a single, anonymous value, :math:`\mathbb{K} = \{\bot\}`.
        This means there's only one sub-table which is equal to the original table, :math:`R`.

    -   Second, map all the rows of each sub-table, :math:`R_k`, to aggregate values, reducing each sub-table to a row in a new group-by table.
        While the aggregate functions are specified in the SQL ``SELECT`` clause, they are applied to the sub-table created by the group-by function.
        The :math:`A_0(R_k), \dots, A_p(R_k)` functions compute the collection of aggregate values for all rows in a sub-table.

        Each expression, :math:`A_p(R_k)`, is a lambda over a sub-table, :math:`\lambda R_k.A_p(R_k)`.
        Consider summation, for example: :math:`\lambda R_k.\sum\limits_{r \in R_k}r`.
        The SQL syntax summarizes a fair amount of detail.

        Aggregate functions include sum, mean, count, min, max, among others.
        There are two variants: the default behavior creates a list of values; the ``DISTINCT`` variant creates a set of only the distinct values.
        Additionally, the key values are also available as a :math:`\lambda R_k.k` lambda.

        When there's no group-by, there's a single table that is summarized by the aggregate functions.

        This creates a new table, :math:`R_k^\Sigma`. Each row is the result of aggregate computations over
        a sub-table, :math:`R_k`, for all :math:`k \in \mathbb{K}`.
        :math:`R_k^\Sigma = \{k \in \mathbb{K} \mid k + \langle A_0(R_k), \dots, A_p(R_k) \rangle \}`.

    -   Important. If there is no ``GROUP BY`` clause and no aggregates, no transformation occurs: :math:`R_k^\Sigma = R`.
        (Since there can be no ``HAVING`` clause without a ``GROUP BY`` clause, with no ``GROUP BY``, processing is effectively finished when there's no ``GROUP BY``.)

-   Having filter, :math:`R_k^{\Sigma^\prime} = H_{C_h(r)}(R_k^\Sigma)`.

    This applies a condition, :math:`C_h(r)`, to each row in the group-by result to pass matching rows, creating a subset, :math:`R_k^{\Sigma^\prime} \subseteq R_k^\Sigma`. Absent a ``HAVING`` clause, :math:`C_h(r) = \mathtt{True}`, and all rows are kept.

    This is essentially identical to the Where filter processing, :math:`T^{*^\prime} = W_{C_w(r)}(T^{*})`.

Yes, the order these functions are applied is not the order ``SELECT`` statements are commonly written.


We can think of this as a composite function.
We can rearrange things so it is closer to ``SELECT`` syntax.

..  math::

    Q(T) = (S_{E_m(r), \dots; A_p(R_k), \dots} \circ F \circ W_{C_w(r)} \circ G_{K(r), \dots} \circ H_{C_h(r)})(T)

The above expression is similar to the more commonly-used order of clauses.

What's important are these features:

1.  The sequence of operations is based on higher-order functions ``filter()``, ``map()`` ``reduce()``, and one ordinary ``product()`` function.

2.  The sequence applies to "composite" rows from a number of tables prior to the ``SELECT`` and new rows from a single table after the ``SELECT``.

3.  All SQL expressions are functions that apply to rows of a table. In the case of the ``SELECT`` expressions that are scalar, and the ``WHERE`` expression, the "row" is a composite object from the :math:`T^{*}` interim result. In the case of the aggregate ``SELECT`` epxressions and the ``HAVING`` expression, the row is a simple row of values.

Here's the way higher-order functions apply to SQL clauses:

..  csv-table::
    :header: Clause, Function

    ``FROM``,``itertools.product()`` to create :math:`\prod T`.
    ``WHERE``,``filter()`` using :math:`C_w(r)`.
    ``SELECT``,``map()`` applied for each :math:`E_m(r)`.
    ``GROUP BY``,``reduce()`` to create :math:`R_k` and compute the summary :math:`A_p(R_k)`.
    ``HAVING``,``filter()`` using :math:`C_h(r)`.

Therefore::

    filter(h, reduce(g, map(s, filter(w, itertools.product(T)))))

Is a conceptual overview of the SQL operation.


The Group By Alternatives
=========================

There are four cases for ``GROUP BY`` and aggregate functions in the ``SELECT`` clause:

-   Neither ``GROUP BY``, nor aggregates in ``SELECT``. The results of :math:`R = (S \circ W \circ F)(T)` are complete.

-   No ``GROUP BY``, but one or more aggregates in ``SELECT``. The result is a single summary row.
    It's :math:`R = (G \circ S \circ W \circ F)(T)`, but the group-by operation is a kind of degenerate case;
    it creates a single group and therefore a single result row from the aggregate computation.
    There can be no ``HAVING`` without a ``GROUP BY``.

-   A ``GROUP BY`` clause, and aggregates in ``SELECT``.
    The result is a new table of summary rows, :math:`R = (G \circ S \circ W \circ F)(T)` which can then be processed by the ``HAVING`` clause.

-   A ``GROUP BY`` clause, but no aggregates in ``SELECT``. Not sure what this means.
    SQLite3 appears to ignore the ``GROUP BY`` key definition and produce all rows.
    This doesn't seem completely sensible; it seems more sensible to emit the distinct combinations of key values.

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
    This suggests a wrapper function to pick a row from the result and then pick one value from the chosen row.
    The resulting table has one or more rows, :math:`T = \{r_1, r_2, \dots, r_n\}`.
    The first row has one or more values, :math:`r_1 = \langle v_1, v_2, \dots, v_n \rangle`.
    The value selector function, :math:`V_{n, c}(Q(T)) = {Q(T)_n}_c`, can pick row :math:`n`, and column :math:`c` of the table to retrieve the scalar value.

-   In an ``EXISTS()`` context the subquery producing any result at all means ``EXISTS()`` is ``True``.
    Failing to produce a result means  ``EXISTS()`` is ``False``. A function, :math:`\exists(Q(T))` is applied to see if there was at least one row in the subquery result.

These wrapper functions to get all values from a columns or a specific value from a row and a column are implicit in SQL.
The ``EXISTS()`` function is the only one that's explicit.
The implicit value-extraction is a handy assumption that simplifies SQL slightly.

There are two subquery contexts:

-   Independent. In this case, the subquery has no expressions that reference tables from the parent query.
    The subquery must be executed first, and the resulting value provided to the parent query.

-   Bound. In this case, the subquery has one or more expressions that reference tables from the parent query.
    This means the :math:`Q(T)` function requires a second argument value: :math:`Q(T; r)`, where :math:`r` is the current row in the query that contains the subquery.
    This also means any of the functions :math:`E_m(r)`, :math:`C_w(r)`, or :math:`C_h(r)` may include the results of a subquery.
    For example, :math:`E_m(x) = V_{1,1}(Q_b(T; x))`, describes a scalar result of a bound subquery, :math:`Q_b`.
    This is a ``SELECT`` clause expression, :math:`E_m(x)` with a reference to a subquery.
    One commonly-used function for the ``WHERE`` and ``HAVING`` clauses is the ``EXISTS`` test, :math:`\exists(Q(T; r)`).
    It may also be a function to a value by executing the subquery, :math:`V_{1,1}(Q(T; r))`.

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
        T_w &= Q_{w*}(T, T_w)  \text{ if $T_w \neq \emptyset$}.\\
    \end{cases}

Note there are two variants of the subquery: Initialization, :math:`Q_{w0}`, and the recursion, :math:`Q_{w*}`.
Often the initialization is a ``VALUES`` clause.
The recursion, :math:`Q_{w*}`, is specified as a ``UNION`` or ``UNION ALL`` clause that's syntactically part of the initial ``VALUES`` clause.
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
