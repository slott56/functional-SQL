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

We'll decompose the hugely complicated ``SELECT`` statement into three parts:

-   The ``ORDER BY`` and ``LIMIT`` options that are appended to the result of the set operations.

-   The set operations like ``UNION`` that apply to multiple sub-select statements.

-   The sub-select statement -- the essential ``SELECT FROM WHERE GROUP BY HAVING`` part.

We'll focus on the sub-select, becuase (a) it's central, and (b) the other parts are add-ons.

We'll work with a collection of tables, :math:`T_1` through :math:`T_{n}`.
Each table, :math:`T_{x}`, is a set of rows, :math:`T_x = \{ r_1, r_2, \dots, r_{m} \}`.
Each row, :math:`r`, is a tuple of atomic values, :math:`r = \langle v_1, v_2, \dots \rangle`.

A Query, :math:`Q(\mathbb{T})`, over the collection of tables, :math:`\mathbb{T} = \{T_1, T_2, \dots, T_{n}\}`, is the following:

..  math::

    \begin{aligned}
    R &= S_{E_m(r), \dots} \left( W_{C_w(r)} ( F(\mathbb{T}) ) \right) \\
    Q(\mathbb{T}) &= H_{C_h(r)} \biggl( S_{A_p(r), \dots} \Bigl( G_{K(r)} ( R ) \Bigr) \biggr)
    \end{aligned}

There are five higher-order functions, :math:`H_f(R)`, :math:`G_{r}(T)`, :math:`S_a(T)`, :math:`S_m(T)`, and :math:`W_f(T)`.
There's one ordinary function :math:`F(T)`.
The higher-order functions are parameterized by other functions.
These parameter functions are applied to the individual rows of table collections.

This requires rethinking the order of the clauses.
The order ``FROM t WHERE C_w SELECT e_1, e_2, a_1, a_2, ... GROUP BY k HAVING C_h`` reflects the order in which processing occurs.
The algorithm has the following stages:

-   Create a "from product", :math:`\mathbb{T}^{*} = F(\mathbb{T})`, from the collection of tables :math:`\mathbb{T}`.

    This joins all the tables. It's a kind of :math:`\prod \mathbb{T}`, sometimes stated as :math:`\mathbb{T}^{*} = T_1 \bowtie T_2 \bowtie \dots \bowtie T_n`.

-   Apply a "where filter", :math:`\mathbb{T}^{*^\prime} = W_{C_w(r)}(\mathbb{T}^{*})`.

    This applies a condition, :math:`C_w(r)`, to each row in the joined tables, :math:`r \in \mathbb{T}^{*}`, to pass rows matching the condition.
    This creates a subset, :math:`\mathbb{T}^{*^\prime} \subseteq \mathbb{T}^{*}`.
    :math:`\mathbb{T}^{*^\prime} = \{ r \mid r \in \mathbb{T}^{*} \textbf{ and } C_w(r) \}`.
    In effect, omitting a ``WHERE`` clause makes :math:`C_w(r) = \mathtt{True}`, leading to a cartesian product result.

    A ``JOIN ON`` clause introduces additional logic to :math:`C_w(r)`. In principle, it might imply a sequence of pair-wise joins as the algorithm. While this might be a nice optimization, it doesn't materially alter the processing.
    It is often easier to read than a massive ``WHERE`` clause.

-   Select mapping, :math:`R = S_{E_m(r), \dots}(\mathbb{T}^{*^\prime})`.

    This transforms the filtered rows of :math:`\mathbb{T}^{*^\prime}` to a new table structure, :math:`R`, by computing values or "projecting" values from the source tables.
    Each :math:`E_m(r)` function maps one composite row of values to a single target value.
    The original table identities are lost at this point.
    :math:`R = \{ \langle E_0(r), \dots, E_m(r) \rangle \mid r \in \mathbb{T}^{*^\prime} \}`.

    Note that the :math:`E_m(r)` collection of expressions is a subset of the expressions in the SQL ``SELECT`` clause.
    SQL ``SELECT`` syntax also includes aggregate expressions, :math:`A_p(g)`, even though they're properly part of ``GROUP BY`` processing.

    Each expression, :math:`E_m(r)`, can be viewed as a one-argument lambda, :math:`E_m(r) = \lambda r.E_m`.
    Using this alternate notation might simplify the overall presentation.

-   Group By reduction, :math:`\mathbb{R} = \{R_k \mid k \in \mathbb{K}\}`, where :math:`R_k = \{ r \mid r \in R \textbf{ and } K(r) = k \}`.

    The given :math:`K(r)` function maps each row, :math:`r`, to a key value. (This may be a tuple of atomic values.)
    This function has some universe of values over the rows in :math:`R`, :math:`\mathbb{K} = \{K(r) \mid r \in R\}`.
    This universe of actual values defines the groups that are created.

    Absent any explicit group-by clause, all the data belongs to a single group, and the universe of key values is a single, anonymous value, :math:`\mathbb{K} = \{\bot\}`.
    This means there's only one sub-table, which is the original table, :math:`\mathbb{R} = \{R_\bot\} = \{R\}`.

-   Select aggregate mapping, :math:`\biguplus\mathbb{R} = \{ \langle A_0(R_k), A_1(R_k), \dots, A_p(R_k) \rangle \mid R_k \in \mathbb{R} \}`.
    This creates a new table, :math:`\biguplus\mathbb{R}`, with rows built from applying aggregate functions to each sub-table, :math:`R_k`.
    Additionally, the key value, :math:`k`, is also available aspart of the constructed row. (This can be a tuple of atomic values.)

    While the aggregate functions are specified in the SQL ``SELECT`` clause, they are applied to each sub-table created by the group-by function.
    The :math:`A_0(R_k), \dots, A_p(R_k)` functions compute the collection of aggregate values for all rows in a sub-table.

    Each expression, :math:`A_p(R_k)`, is a lambda over a sub-table, :math:`\lambda R_k.A_p(R_k)`.
    Consider summation, for example: :math:`\lambda R_k.\sum\limits_{r \in R_k}r`.
    The count, as another example, is :math:`\lambda R_k.\sum\limits_{r \in R_k} 1`.

    Aggregate functions include sum, mean, count, min, max, among others.
    There are two variants: the default behavior creates a list of values; the ``DISTINCT`` variant creates a set of only the distinct values.

    When there's no group-by, the resulting table has a single row computed by the aggregate functions.

    Important. If there is no ``GROUP BY`` clause and no aggregate functions, no transformation occurs: :math:`\biguplus\mathbb{R} = R`.
    (Since there can be no ``HAVING`` clause without a ``GROUP BY`` clause, with no ``GROUP BY``, processing is effectively finished when there's no ``GROUP BY``.)

    Note. If there's a ``GROUP BY`` clause and no aggregate functions, the SQL seems invalid.

-   Apply a "having filter", :math:`\biguplus\mathbb{R}^{\prime} = H_{C_h(r)}(\biguplus\mathbb{R})`. This is identical to where-clause processing.

    This applies a condition, :math:`C_h(r)`, to each row in the group-by result, :math:`\biguplus\mathbb{R}`, to pass matching rows.
    This creates a subset, :math:`\biguplus\mathbb{R}^{\prime} \subseteq \biguplus\mathbb{R}`.
    :math:`\biguplus\mathbb{R}^{\prime} = \{ r \mid r \in \biguplus\mathbb{R} \textbf{ and } C_h(r) \}`.

    Absent a ``HAVING`` clause, :math:`C_h(r) = \mathtt{True}`, and all rows are kept.

Yes, the order these functions are applied is not the order ``SELECT`` statements are commonly written.


We can think of this as a composite function.
We can rearrange things so it is closer to ``SELECT`` syntax.

..  math::

    Q(\mathbb{T}) = (S_{E_m(r), \dots; A_p(R_k), \dots} \circ F \circ W_{C_w(r)} \circ G_{K(r), \dots} \circ H_{C_h(r)})(\mathbb{T})

The above expression is similar to the more commonly-used order of clauses.

What's important are these features:

1.  The sequence of operations is based on higher-order functions ``filter()``, ``map()`` ``reduce()``, and one ordinary ``product()`` function.

2.  The sequence applies to "composite" rows from a number of tables prior to the ``SELECT`` and new rows from a single table after the ``SELECT``.

3.  All SQL expressions are functions that apply to rows of a table. In the case of the ``SELECT`` expressions that are scalar, and the ``WHERE`` expression, the "row" is a composite object from the :math:`T^{*}` interim result. In the case of the aggregate ``SELECT`` epxressions and the ``HAVING`` expression, the row is a simple row of values.

Here's the way higher-order functions apply to SQL clauses:

..  csv-table::
    :header: Clause, Function

    ``FROM``,``itertools.product()`` to create :math:`\mathbb{T}^*`.
    ``WHERE``,``filter()`` using :math:`C_w(r)`.
    ``SELECT``,``map()`` applied for each :math:`E_m(r)`.
    ``GROUP BY``, "Partition using :math:`K(r)` to create :math:`\mathbb{R}`."
    , "``reduce()`` to compute aggregates using :math:`A_p(R_k)`."
    ``HAVING``,``filter()`` using :math:`C_h(r)`.

Therefore,::

    filter(h,
        reduce(s_a,
            parition(k,
                map(s_e,
                    filter(w,
                        itertools.product(T))))))

This is a conceptual overview of the SQL operation.
The tricky part is the ``partition()`` function isn't built-in to ``itertools``.
This function can be more usefully created around a ``defaultdict(list)`` structure to create lists of rows in each partition.
Each of these lists can then be aggregated and filtered.

The Group By Alternatives
=========================

There are four cases for ``GROUP BY`` and aggregate functions in the ``SELECT`` clause:

-   Neither ``GROUP BY``, nor aggregates in ``SELECT``. The results of :math:`R = (S_E \circ W \circ F)(\mathbb{T})` are complete.

-   No ``GROUP BY``, but one or more aggregates in ``SELECT``. The result is a single summary row.
    It's :math:`R = (S_A \circ S_E \circ W \circ F)(\mathbb{T})`, but the group-by operation is a kind of degenerate case;
    it creates a single group and therefore a single result row from the aggregate computation, :math:`S_A`.
    There can be no ``HAVING`` without a ``GROUP BY``.

-   A ``GROUP BY`` clause, and aggregates in ``SELECT``.
    The result is a new table of summary rows, :math:`R = (S_A \circ G \circ S_E \circ W \circ F)(\mathbb{T})`. This can then be processed by the ``HAVING`` clause.

-   A ``GROUP BY`` clause, but no aggregates in ``SELECT``. Not sure what this means.
    SQLite3 appears to ignore the ``GROUP BY`` key definition and produce all rows.
    This doesn't seem completely sensible; it seems more sensible to emit the distinct combinations of key values.

..  comment: not sure where this goes...

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

For the ``FROM`` clause, the subquery provies a table. This is consistent with the definition of :math:`Q(\mathbb{T})` above.

For the other clauses, there are three kinds of results: a set of values, a single value, or a boolean.

-   The subquery produces a set of values used for collection operators like ``IN`` or ``NOT IN``.
    This suggests a value selector function can pick values from a single column of the result.
    The value selector, :math:`V_c(Q(\mathbb{T}))`, will pick one column, :math:`c` from all rows, :math:`V_c(Q(\mathbb{T})) = \{r_c \mid r \in Q(\mathbb{T}) \}`, to create a set of values.

-   The subquery produces a single value for scalar operators.
    This suggests a wrapper function to pick a row from the result and then pick one value from the chosen row.
    The resulting table has one or more rows, :math:`T = \{r_1, r_2, \dots, r_n\}`.
    The first row has one or more values, :math:`r_1 = \langle v_1, v_2, \dots, v_n \rangle`.
    The value selector function, :math:`V_{n, c}(Q(\mathbb{T}))`, can pick row :math:`n`, and column :math:`c` of the table to retrieve the scalar value.
    Most of the time, this is :math:`V_{1, c}` to pick a column from the first (or only) row.

-   In an ``EXISTS()`` context the subquery producing any result at all means ``EXISTS()`` is ``True``.
    Failing to produce a result means  ``EXISTS()`` is ``False``.
    A function, :math:`\exists(Q(\mathbb{T}))` is applied to see if there was at least one row in the subquery result.

These wrapper functions to get all values from a columns or a specific value from a row and a column are implicit in SQL.
The ``EXISTS()`` function is the only one that's explicit.
The implicit value-extraction is a handy assumption that simplifies SQL slightly.

There are two subquery contexts:

-   Independent. In this case, the subquery has no expressions that reference tables from the parent query.
    The subquery must be executed first, and the resulting value provided to the parent query.

-   Bound. In this case, a subquery has one or more expressions that reference tables from the context query.
    This means the :math:`Q(\mathbb{T})` function requires a second argument value: :math:`Q(\mathbb{T}; r)`, where :math:`r` is the current row in the context query.
    This also means any of the functions :math:`E_m(r)`, :math:`C_w(r)`, or :math:`C_h(r)` may include the results of a subquery.
    For example, :math:`E_m(x) = V_{1,1}(Q_b(\mathbb{T}; x))`, extracts a scalar result of a bound subquery, :math:`Q_b`, when applied to a collection of tables with a context row, :math:`x`.
    This can happen when a ``SELECT`` clause expression, :math:`E_m(x)` has a reference to a subquery.

    One commonly-used function for the ``WHERE`` and ``HAVING`` clauses is the ``EXISTS`` test, :math:`\exists(Q(\mathbb{T}; r)`).
    This may include a function of a scalar result of a bound subquery, :math:`V_{1,1}(Q_b(\mathbb{T}; r))`, in an more complex condition.

Rows from the context query are available in a bound subquery, :math:`Q_b`, in SQL without any special syntax.
What's essential here is the subquery processing has very handy implicit behavior.


Common Table Expressions
========================

A **Common Table Expression** (**CTE**) has a creation query, :math:`Q_w`, prior to a target query.
These are specified in a ``WITH`` clause, prior to the target select.
The creation query prepares a table-like structure that can be incorporated into another query.

..  math::

    Q(\mathbb{T} \cup \{ Q_{W_1}(\mathbb{T}), Q_{W_2}(\mathbb{T}), \dots \} )

Additionally, the creation query can involve recursion.

..  math::

    Q_W(\mathbb{T}) = \begin{cases}
        T_w &= Q_{W0}(\mathbb{T})  \text{ initially},\\
        T_w &= Q_{W*}(\mathbb{T} \cup \{T_w\})  \text{ if $T_w \neq \emptyset$}.\\
    \end{cases}

Note there are two variants of the subquery: an initialization clause, :math:`Q_{W0}`, and a recursion clause, :math:`Q_{W*}`.
Often the initialization clause is a ``VALUES`` clause providing literal values.
The recursion, :math:`Q_{W*}`, is specified as a ``UNION`` or ``UNION ALL`` clause that's syntactically part of the initial ``VALUES`` clause.
The choice between breadth-first and depth-first traversal of the query results is specified with an ``ORDER BY`` clause.
The default is breadth-first.

Other Query Features
====================

Some "other" features of SQL queries include the following:

-   Order BY. This is best handled by Python's native :py:func:`sorted` function.
    ``sorted(fetch(Q), key=lambda row: ...)``.

-   Limit. This can be handled by Python's native list slicing.
    ``list(fetch(Q))[start:stop]``.

    However, this can be handled better by applying a filter to the enumerated rows.
    ``(r for n, r in enumerate(fetch(Q), start=1) if start <= n < stop)``.
    We can imagine a ``limit(query, slice(start, stop, step))`` iterator that yields the expected subset.

-   Union, Intersect, etc. There are set operations that are part of Python.
    The complication here is that the underlying :py:class:`sqlful.Row` objects are mutable dictionaries.
    To do set operations, it's best to make immtutable, frozen dataclasses.

These can all be done with relative ease.
There isn't any SQL-like syntax for these features.
