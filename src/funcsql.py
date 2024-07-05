"""
Some SQL-like processing in (mostly) functional-style Python.

We want to express something like the following

::

    SELECT expr as name, expr as name
    FROM data_source, data_source
    WHERE expression
    GROUP BY name
    HAVING expression

As pure Python

::

    (
    Select(name=lambda jr: expr, name=lambda jr: expr)
    .from_(data_source, data_source)
    .where(lambda jr: expression)
    .group_by("name")
    .having(lambda row: expression)
    )

Lambdas permit applying the expression during query processing time.
The ``jr`` is a "Join Row" where each table in the ``FROM`` clause is present.
In the ``having`` clause, it's a simpler "Row" based on the computed values.

The idea is this will work **outside** any database.
Not even the horrid SQLite hack-around
where a temporary in-memory database is used to do GROUP-BY and aggregate processing.

"""

from collections.abc import Callable, Iterable, Iterator
from collections import defaultdict
from functools import partial
from itertools import product
from operator import attrgetter
from types import FunctionType
from typing import Any, Self, cast, DefaultDict


class Table:
    """
    The foundational collection of data consumed by a query.

    A Table produces :py:class:`funcsql.Row` objects, but doesn't necessarily contain them.
    The structure in this class is a ``list[dict[str, Any]]``.
    From these, :py:class:`funcsql.Row` objects are created.

    A table has an internal name that's used by the query.
    This should match the Python variable name, but that's not a requirement.

    The **external** Python variable is only used in the :py:meth:`funcsql.Select.from_` method.
    The **internal** string name is used in all lambdas throughout the query.

    Example

    >>> t = Table("t", [
    ...     {'col1': 'row1-colum1', 'col2': 42},
    ...     {'col1': 'row2-colum1', 'col2': 43},
    ... ])
    >>> list(t)
    [Row('t', **{'col1': 'row1-colum1', 'col2': 42}), Row('t', **{'col1': 'row2-colum1', 'col2': 43})]

    ..  important::

        Table names **must** be valid Python identifiers.

        Column names **must** be valid Python identifiers.

    The data source for a table can can be raw (external) data or
    it could be  results of query execution.

    Subclasses can support a wide variety of collections.

    -   list[list[str]] supplied with a schema (i.e. CSV reader + headers).

    -   list[JSONDoc] with JSONSchema schema definition from NDJSON files.
    """

    def __init__(
        self,
        name: str,
        data: Iterable[dict[str, Any]] | None = None,
        schema: list[str] | None = None,
    ) -> None:
        """
        Create a new table.

        :param name: The internal name of the table.
        :param data: The sequence of data items.
        :param schema: A schema to provide column names.
        """
        self.name = name
        self.rows: list[dict[str, Any]] = list(data) if data else []
        self.schema = schema

    def load(self, data: Iterable[dict[str, Any]]) -> None:
        """Replace the underlying data with this data."""
        self.rows = list(data)

    def column_names(self) -> list[str]:
        """Expose the column names. Useful for ``SELECT *`` constructs."""
        if self.schema is None:
            self.schema = list(self.rows[0].keys())
        return self.schema

    def __iter__(self) -> Iterator["Row"]:
        return (Row(self.name, **r) for r in self.rows)

    def alias_iter(self, alias: str) -> Iterator["Row"]:
        """Apply a table alias."""
        return (Row(alias, **r) for r in self.rows)

    @classmethod
    def from_rows(cls, table_name: str, rows: Iterable["Row"]) -> "Table":
        """Builds a table from a sequence of rows -- possibly a UNION of multiple queries."""
        return Table(table_name, (r._asdict() for r in rows))

    @classmethod
    def from_query(cls, table_name: str, query: "Select") -> "Table":
        """Builds a table by fetching the results of the given query."""
        return Table.from_rows(table_name, fetch(query))


class Row:
    """
    An immutable collection of column names and values.

    Subclasses can be created to wrap a variety of collections,
    including dataclasses or Pydantic ``base_model`` instances.
    """

    def __init__(self, table: str, **columns: Any) -> None:
        self._table = table
        self._columns = columns

    def __getattr__(self, name: str) -> Any:
        return self._columns[name]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._table!r}, **{self._columns!r})"

    def _asdict(self) -> dict[str, Any]:
        """Return the row as a dictionary."""
        return self._columns

    def _values(self) -> list[Any]:
        """Rerturn only the values from this row."""
        return list(self._columns.values())

    def __eq__(self, other: Any) -> bool:
        match other:
            case Row() as row:
                return self._table == row._table and self._columns == row._columns
            case _:  # pragma: no cover
                return NotImplemented


class QueryComposite:
    """
    A collection of ``Row`` instances from one or more named Tables.
    This provides attribute navigation through the columns of the tables in this composite.

    >>> qc = QueryComposite(Row("t1", a=1), Row("t2", b=2))
    >>> qc.t1.a
    1
    >>> qc.t2.b
    2
    """

    def __init__(self, *table_rows: Row, context: "QueryComposite | None" = None) -> None:
        self._rows = {row._table: row for row in table_rows if row is not None} | (
            context._rows if context else {}
        )

    def __getattr__(self, name: str) -> Row:
        try:
            return self._rows[name]
        except KeyError as ex:  # pragma: no cover
            print(f"is {name} a valid table? names are {self._rows.keys()}")
            raise

    def __repr__(self) -> str:
        return repr(self._rows)


class Aggregate:
    """
    Wrapper for an aggregate function to summarize.

    There are three forms for using this:

    -   ::

            m_x = Aggregate(mean, "x"), x = lambda jr: jr.table.column

        The ``x=expr`` defines the raw value to summarize.
        This value is then referred to by name in the ``Aggregate()`` constructor.
        (Yes, the ``x=`` is defined later, but name resolution doesn't happen until the query is run.)

    -   ::

            m_x = Aggregate(mean, lambda jr: jr.table.column)

        Same as above. A column name is made up for the expression.

    -   ::

            count = Aggregate(count, "*")

        A special case.

    Many SQL aggregates are first-class parts of Python.

    ..  csv-table::

        AVG,:py:func:`statistics.mean`
        COUNT,We define a special :py:func:`functsql.count` function to ignore None.
        MAX,:py:func:`max`
        MIN,:py:func:`min()`
        SUM,:py:func:`sum()`
        STDEV,:py:func:`statistics.stdev`

    ..  TODO:: Offer ``DISTINCT`` variants to reduce to a set before computation.
    """

    def __init__(
        self,
        reduction_function: Callable[[Iterable[Any]], Any],
        name: str | Callable[[QueryComposite], Any],
    ) -> None:
        self.reduction_function = reduction_function
        match name:
            case str() if name == "*":
                # Add _id = True to SELECT, do function(_id).
                self.function = lambda qc: True
                self.name = f"_{id(self.function)}"
                self.add_to_select = {self.name: self.function}
            case str():
                # SELECT has name=lambda, do function(name)
                self.name = name
                self.function = attrgetter(self.name)
                self.add_to_select = {}
            case FunctionType() as some_lambda:
                # Add _id = lambda to SELECT, do function(_id)
                self.name = f"_{id(some_lambda)}"
                self.function = attrgetter(self.name)
                self.add_to_select = {self.name: some_lambda}
            case _:  # pragma: no cover
                raise ValueError(f"unknown {type(name)=}")

    def value(self, rows: Iterable[Row]) -> Any:
        raw = map(self.function, rows)
        return self.reduction_function(raw)


def count(values: Iterable) -> int:
    """Handy aggregate function to skip NONE's"""
    return sum(1 for v in values if v is not None)


class SelectStar:
    """
    A way to handle ``SELECT *``.
    This is provided **instead** of any ``name=expr`` parameters to :py:class:`funcsql.Select`.

    This reaches into the from clause and join clause tables and extracts the schema information.

    In the event of duplicate column names in a multi-table join, the last one will be used.
    """

    def schema_expr(self, from_clause: dict[str, Table]) -> dict[str, Callable]:
        names = [
            (name, colname)
            for name, table in from_clause.items()
            for colname in table.column_names()
        ]
        getter_partials = {
            col: lambda c, tbl=tbl, col=col: getattr(getattr(c, tbl), col) for tbl, col in names
        }
        return getter_partials


STAR = SelectStar()


class Select:
    """
    Creates the query, starting with the  SELECT clause.

    For ``SELECT *`` queries, the ``star`` parameter must be ``STAR``.

    For all other query forms, use ``name=lambda qc: expr`` constructs.
    This is equivalent to ``expr AS name`` in SQL.

    The expression can contain ``table.column`` references using ``qc.table.column``.
    The full name must be provided: we don't attempt to deduce the
    table that belongs with a name.

    The expression can contain any other Python literal of function.

    ..  code-block:: SQL

        SELECT label, 3*val+1 as answer, 42 as literal
        FROM table

    ..  code-block:: Python

        Select(
            label=lambda qc:qc.table.label,
            answer=lambda qc: 3 * qc.table.val + 1,
            literal=lambda qc: 42
        )

    Each expression must be a function (or lambda or callable object) that accepts
    a single :py:class:`funcsql.QueryComposite` object and returns a useful value.
    """

    def __init__(
        self,
        star_: SelectStar | None = None,
        **name_expr: Callable[[QueryComposite], Any] | Aggregate,
    ) -> None:
        """
        The star value must be a instance of :py:class:`funcsql.SelectStar` or None.

        All other columns must use named parameters, name=expression.
        The expression must be a lambda (or function) that uses a ``QueryContext`` argument.
        """
        if star_ and not isinstance(star_, SelectStar):  # pragma: no cover
            raise TypeError("likely an expression missing a name")
        self.star: SelectStar | None = star_
        self.select_clause: dict[str, Callable[[QueryComposite], Any] | Aggregate] = name_expr

        # Init the other clauses
        self.from_clause: dict[str, Table] = {}
        self.where_clause: list[Callable[[QueryComposite], bool]] = []
        self.group_by_clause: tuple[str, ...] = cast(tuple[str], ())
        self.having_clause: Callable[[Row], bool] = lambda c: True

        # Partition the initial SELECT list:
        # - Aggregate functions (set aside to be computed later)
        # - All other expressions to be computed ASAP.
        self.select_clause_agg: dict[str, Aggregate] = {}
        self.select_clause_simple: dict[str, Callable[[QueryComposite], Any]] = {}
        for name, function in self.select_clause.items():
            match function:
                case Aggregate() as agg:
                    self.select_clause_agg[name] = agg
                    if agg.add_to_select:
                        self.select_clause_simple |= agg.add_to_select
                case _ as simple:
                    self.select_clause_simple[name] = simple

    def from_(self, *tables: Table, **named_tables: Table) -> Self:
        """
        The FROM clause: the tables to query.
        Table aliases aren't required if all the table names are unique.

        To do a self-Join, the tables require an alias.
        The alias will be used in QueryComposite objects.

        ..  code-block:: SQL

            SELECT e.name as employee, m.name as manager
            FROM employees e, employees m
            WHERE ...

        ..  code-block:: Python

            (
                Select(
                    employee=lambda qc: qc.e.name,
                    manager=lambda qc: qc.m.name
                )
                .from_(e=employees, m=employees)
                .where(...)
            )

        This method also expands ``SELECT *`` into proper names.
        """
        self.from_clause = {t.name: t for t in tables}
        self.from_clause |= named_tables
        if self.star:
            self.select_clause_simple.update(self.star.schema_expr(self.from_clause))
        return self

    def join(
        self, table: Table | None = None, *, on_: Callable[[QueryComposite], bool], **alias: Table
    ) -> Self:
        """
        The JOIN table ON condition clause: a table to query and the join condition for that table.

        ..  code-block:: SQL

            SELECT e.name as employee, m.name as manager
            FROM employees e
            JOIN employee m ON e.manager_id = m.employee_id

        ..  code-block:: Python

            (
                Select(
                    employee=lambda qc: qc.e.name,
                    manager=lambda qc: qc.m.name
                )
                .from_(e=employees)
                .join(m=employee, on_=lambda qc: qc.e.manager_id == qc.m.employee_id)
            )

        In principle, this **could** lead to an optimization where pair-wise table joins are done
        to build the final ``QueryComposite`` objects.

        This doesn't handle any of the outer join operators.

        ..  TODO:: [LEFT | RIGHT | FULL] OUTER? JOIN

            An implicit union of non-matching rows.
            An additional "filterfalse()`` is required to provide NULL-filled missing rows.

        ..  TODO:: ``USING("col1", "col2")`` builds ``labmda qc: qc.table.col1 == qc.?.col1``

            Based on left and right sides of ``join(table, using=("col1", "col2"))``.
        """
        if table and alias:  # pragma: no cover
            raise TypeError("join on clause requires a table or alias=table, not both")
        if table:
            self.from_clause[table.name] = table
        elif alias:
            self.from_clause |= alias
        else:  # pragma: no cover
            raise TypeError("join on clause requies a table or alias=table")
        self.where_clause.append(on_)
        return self

    def where(self, function: Callable[[QueryComposite], bool]) -> Self:
        """
        The WHERE clause: an expression used for joining and filtering.

        ..  code-block:: SQL

            SELECT e.name as employee, m.name as manager
            FROM employees e, employees m
            WHERE e.manager_id = m.employee_id

        ..  code-block:: Python

            (
                Select(
                    employee=lambda qc: qc.e.name,
                    manager=lambda qc: qc.m.name
                )
                .from_(e=employees, m=employees)
                .where(lambda qc: qc.e.manager_id == qc.m.employee_id)
            )
        """
        self.where_clause.append(function)
        return self

    def group_by(self, *name: str, **named_expr: Callable[[QueryComposite], Any]) -> Self:
        """
        The GROUP BY clause: a list of names or a list of name=expr expressions.

        If names are provided, they *must* be names computed by the ``SELECT`` clause.

        If name=expr is used, the name=expr is added to the ``SELECT`` clause.

        ..  code-block:: SQL

            SELECT deparment_id, count(*)
            FROM employees
            GROUP BY department_id

        ..  code-block:: Python

            (
                Select(
                    department_id=lambda qc: qc.employees.department_id
                    count=Aggregate(count, "*")
                )
                .from_(employees)
                .group_by("department_id")
            )
        """
        if name and named_expr:  # pragma: no cover
            raise TypeError("group by clause requires either names or name=lambda, not both")
        if name:
            self.group_by_clause = name
        elif named_expr:
            for expr_name, expr in named_expr.items():
                match expr:
                    case FunctionType() as expr:
                        self.select_clause_simple[expr_name] = expr
                    case _:  # pragma: no cover
                        raise TypeError("invalid object in {expr_name}={expr}")
            self.group_by_clause = tuple(named_expr.keys())
        else:  # pragma: no cover
            raise TypeError("group by clause requires either names or name=lambda")

        return self

    def having(self, function: Callable[[Row], bool]) -> Self:
        """
        The HAVING clause: an expression to filter groups.

        The expression will operate on :py:class:`funcsql.Row` objects.
        It does **not** operate on ``QueryComposite`` objects.

        ..  code-block:: SQL

            SELECT deparment_id, count(*)
            FROM employees
            GROUP BY department_id
            HAVING count(*) > 2

        ..  code-block:: Python

            (
                Select(
                    department_id=lambda qc: qc.employees.department_id
                    count=Aggregate(count, "*")
                )
                .from_(employees)
                .group_by("department_id")
                .having(lambda row: row.count > 2)
            )

        The groups are not built from ``QueryComposite`` objects; they're simpler :py:class:`funcsql.Row` objects.
        """
        if not self.group_by_clause:  # pragma: no cover
            raise TypeError("having clause requires a group by clause")
        self.having_clause = function
        return self

    def __repr__(self) -> str:  # pragma: no cover
        s = repr(self.select_clause)
        f = repr(self.from_clause)
        w = repr(self.where_clause)
        g = repr(self.group_by_clause)
        h = repr(self.having_clause)
        return f"Select(**{s}).from_({f}).where({w}).group_by({g}).having({h})"

    def __iter__(self) -> Iterator[Row]:
        return fetch(self)


def from_product(
    query: Select, context: "QueryComposite | None" = None
) -> Iterable[QueryComposite]:
    """
    FROM clause creates an iterable of :py:class:`funcsql.QueryComposite` objects as a product of source tables.

    :param query: The :py:class:`funcsql.Select` object
    :param context: An optional context used for subqueries.
    :return: product of all rows of all tables
    """
    join = product(*(table.alias_iter(name) for name, table in query.from_clause.items()))
    return (QueryComposite(*row_tuple, context=context) for row_tuple in join)


def where_filter(query: Select, composites: Iterable[QueryComposite]) -> Iterator[QueryComposite]:
    """
    WHERE clause filters the iterable :py:class:`funcsql.QueryComposite` objects.

    :param query: The :py:class:`funcsql.Select` object
    :param composites: An iterable source of :py:class:`funcsql.QueryComposite` objects
    :return: An iterator overn :py:class:`funcsql.QueryComposite` objects.

    ..  todo:: Outer Joins are implemented here.
    """
    yield from filter(lambda qc: all(cond(qc) for cond in query.where_clause), composites)
    # yield from outer join missing rows.


def star_star_map(func: Callable[..., Any], items: Iterable[Any]) -> Any:
    return (func(**item) for item in items)


key = lambda item: item[0]
value = lambda item: item[1]


def select_map(query: Select, composites: Iterable[QueryComposite]) -> Iterator[Row]:
    """
    SELECT clause applies all non-aggregate computations to the :py:class:`funcsql.QueryComposite` objects.

    :param query: The :py:class:`funcsql.Select` object
    :param composites: An iterable source of :py:class:`funcsql.QueryComposite` objects
    :return: an iterator over :py:class:`funcsql.Row` instances.
    """
    row_builder = lambda composite: {
        name: func(composite) for name, func in query.select_clause_simple.items()
    }
    dicts = map(row_builder, composites)
    anonymous_row = partial(Row, "")
    return star_star_map(anonymous_row, dicts)

    # Alternatively:
    # return (
    #     Row("", **{name: func(composite) for name, func in query.select_clause_simple.items()})
    #     for composite in composites
    # )


def aggregate_map(
    select_clause_agg: dict[str, Aggregate], groups: dict[tuple[Any, ...], Iterable[Row]]
) -> Iterator[Row]:
    """
    Applies ``Aggregate`` computations to grouped rows.

    Very similar to the way the :py:func:`funcsql.select_map` function works.

    :param select_clause_agg: the aggregate functions from a :py:class:`funcsql.Select` object
    :param groups: the key: list[value] mapping with groups built from raw data.
    :return: an iterator over :py:class:`funcsql.Row` instances.
    """

    row_builder = lambda group_k_v: dict(key(group_k_v)) | {
        name: agg.value(value(group_k_v)) for name, agg in select_clause_agg.items()
    }
    dicts = map(row_builder, groups.items())
    anonymous_row = partial(Row, "")
    return star_star_map(anonymous_row, dicts)

    # Alternatively:
    # return (
    #     Row(
    #         "",
    #         **(
    #             dict(key)  # The group-by column(s)
    #             | {
    #                 name: agg.value(values) for name, agg in select_clause_agg.items()
    #             }  # The aggregates
    #         ),
    #     )
    #     for key, values in groups.items()
    # )


def group_reduce(query: Select, select_rows: Iterable[Row]) -> Iterator[Row]:
    """
    GROUP BY clause either creates groups and summaries, or passes data through.

    There are three cases:

    -   Group by with no aggregate functions. This will be a collection of group keys.

    -   Aggregate functions with no Group by. This is a single summary aggregate applied to all data.
        Think ``SELECT COUNT(*) FROM table``.

    -   Neither Group by nor aggregate functions. The data passes through.

    :param query: The :py:class:`funcsql.Select` object
    :param select_rows: iterable sequence of  :py:class:`funcsql.Row` objects
    :return: iterator over  :py:class:`funcsql.Row` objects
    """
    # Provide a very permissive hint for ``groups``
    groups: dict[tuple[Any, ...], Iterable[Row]] = defaultdict(list)

    if query.group_by_clause:
        # GROUP BY clause, cluster select_rows by keys and compute aggregates.
        for row in select_rows:
            key = tuple((k, getattr(row, k)) for k in query.group_by_clause)
            # Well, actually... for Iterable[row] -- it's actually a list[Row].
            cast(list, groups[key]).append(row)

        # Compute any aggregate values for each group.
        # If no aggregates, the group-by keys are the row's content.
        return aggregate_map(query.select_clause_agg, groups)

    elif query.select_clause_agg:
        # Aggregate functions without a GROUP BY clause, single-row summary.
        groups[()] = list(select_rows)
        return aggregate_map(query.select_clause_agg, groups)

    # Neither GROUP BY nor summary aggregate.
    # Can't use ``aggregate()`` in this case.
    # We may have duplicate rows; something the ``groups`` dict can't handle.
    return iter(select_rows)


def having_filter(query: Select, group_rows: Iterable[Row]) -> Iterator[Row]:
    """
    HAVING clause filters the groups.

    This is similar to :py:func:`funcsql.where_filter`.

    :param query: The :py:class:`funcsql.Select` object
    :param select_rows: iterable sequence of  :py:class:`funcsql.Row` objects
    :return: iterator over  :py:class:`funcsql.Row` objects
    """
    return filter(query.having_clause, group_rows)


def fetch(query: Select, context: "QueryComposite | None" = None) -> Iterator[Row]:
    """
    The essential SQL algorithm.

    ..  math::

        Q(T) = H \\biggl( G \\Bigl( S \\left( W ( F(T) ) \\right) \\Bigr) \\biggr)

    Where

    -   :math:`H` is :py:func:`funcsql.from_product`.
    -   :math:`G` is :py:func:`funcsql.group_reduce`, which uses :py:func:`funcsql.aggregate_map`
    -   :math:`S` is :py:func:`funcsql.select_map`.
    -   :math:`W` is :py:func:`funcsql.where_filter`.
    -   :math:`F` is :py:func:`funcsql.from_product`.

    Inverting these function, the order of operations is:

    1.  FROM -- Creates table-like creature with ``QueryComposite`` rows.
    2.  WHERE -- filters ``QueryComposite`` rows.
    3.  SELECT -- creates a ``Table`` with simple ``Row`` instances, but no name.
    4.  GROUP BY -- creates a second table with ``Row`` instances and no name.
    5.  HAVING -- filters the second table

    :param query: The Query that provides Row instances.
    :param context:  A context used for subqueries that depend on a context query.
    :return: Row instances.
    """
    # Stacked...
    # # FROM emits QueryComposites.
    # composites = from_product(query, context)
    #
    # # WHERE clause filters the iterable QueryComposites.
    # joined = where_filter(query, composites)
    #
    # # SELECT clause applies all non-aggregate computations.
    # select_rows = select_map(query, joined)
    #
    # # GROUP BY and aggregation,
    # group_rows = group_reduce(query, select_rows)
    #
    # # Apply HAVING clause to the grouped rows
    # return having_filter(query, group_rows)

    # Nested...
    return having_filter(
        query,
        group_reduce(query, select_map(query, where_filter(query, from_product(query, context)))),
    )


def fetch_first_value(query: Select) -> Any:
    """
    Fetches the first row's first column value.
    Implements cases where subquery produces a scalar value.
    """
    try:
        row = next(fetch(query))
        return row._values()[0]
    except StopIteration:
        return None


def fetch_all_values(query: Select) -> Iterator[Any]:
    """
    Fetches the all row's first column values.
    Implements cases where subquery produces a set of values.

    For example, ``WHERE col IN (SELECT ...)``.
    """
    return (row._values()[0] for row in fetch(query))


def fetch_table(table_name: str, query: Select) -> Table:
    """
    Createes a Table from the results of a query.
    Implements cases where subquery is in the ``FROM`` clause.
    """
    return Table.from_query(table_name, query)


def exists(context: QueryComposite, query: Select) -> bool:
    """
    Did a suquery fetch any rows?
    Implements the ``EXISTS()`` function.

    :param context:  A context used for subqueries that depend on a context query.
    :param query: The Query that provides Row instances.
    :return: True if any row was built by the query.

    ..  note::

        The order of the arguments is reversed from :py:func:`funcsql.fetch` because
        this is used in a query builder where a context is generally required.
    """
    return any(fetch(query, context))

    # Written out the hard way...
    # try:
    #     next(fetch(query, context))
    #     return True
    # except StopIteration:
    #     return False


class Insert:
    """Adds rows to a Table.

    ::

        Insert().into(table).values([{data}])
    """

    def __init__(self) -> None:
        pass

    def into(self, table: Table) -> Self:
        self.table = table
        return self

    def values(self, data: list[dict[str, Any]]) -> Self:
        self.data = data
        return self

    def __call__(self) -> None:
        # TODO: Schema check to be sure self.data appears to be compatible with self.table.column_names()
        self.table.rows.extend(self.data)


class Update:
    """Updates rows in a Table.

    ::

        (
            Update(table)
            .set(col=lambda row: function)
            .where(lambda row: condition)
        )
    """

    def __init__(self, table: Table) -> None:
        self.table = table

    def set(self, **expression: Callable) -> Self:
        self.set_expr = expression
        return self

    def where(self, function: Callable[[Row], bool]) -> Self:
        self.where_clause = function
        return self

    def __call__(self) -> None:
        # TODO: Schema check to be sure self.set_expr.keys() appears to be compatible with self.table.column_names()
        for raw_row in self.table.rows:
            exposed_row = Row(self.table.name, **raw_row)
            if self.where_clause(exposed_row):
                for col, func in self.set_expr.items():
                    raw_row[col] = func(exposed_row)


class Delete:
    """Deletes rows from a table.

    ::

        Delete().from_(table).where(lambda row: condition)
    """

    def __init__(self) -> None:
        pass

    def from_(self, table: Table) -> Self:
        self.table = table
        return self

    def where(self, function: Callable[[Row], bool]) -> Self:
        self.where_clause = function
        return self

    def __call__(self) -> None:
        """
        Not efficient. But. Deleting from a list is touchy.
        """
        self.table.rows = [
            raw_row
            for raw_row in self.table.rows
            if not self.where_clause(Row(self.table.name, **raw_row))
        ]
