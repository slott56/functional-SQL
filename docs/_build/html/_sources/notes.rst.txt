#########
Notes
#########

Additional Features
=====================

1.  Replace result returned by :py:func:`funcsql.fetch` to be ``Iterator[Row] | None`` (or raise an exception for no rows.)
    It's awkward to test an iterator for being empty;
    it's much easier to see if the result is an ``Iterator`` or a ``None`` object.
    (Perhaps only :py:func:`funcsql.fetch_select` needs to be changed to simplify :py:func:`funcsql.fetch_recursive`.)
2.  Partitioned Tables.
3.  Implement :py:meth:`funcsql.Table.__add__`, and :py:meth:`funcsql.Table.__iadd__` to do SQL union.
4.  Implement depth-first recursive query alternative.
5.  Implement union-all recursive query alternative.

Partitioned Tables
------------------

Partitioned tables should be an extention to :py:class:`funcsql.Table` and nothing more.
The use of :py:func:`list` in :py:func:`funcsql.group_reduce` is a potential problem.

1. Fix :py:class:`funcsql.Table` to replace :py:func:`list`.

2. Fix :py:func:`funcsql.group_reduce` to use :py:class:`funcsql.Table` instead of :py:func:`list`.

3. Subclass :py:class:`funcsql.Table` to show how partitioning would work.

Badges
=======

Coverage.

::

        export TOTAL=$(python -c "import json;print(json.load(open('coverage.json'))['totals']['percent_covered_display'])")

See https://dev.to/thejaredwilcurt/coverage-badge-with-github-actions-finally-59fa

See https://nedbatchelder.com/blog/202209/making_a_coverage_badge.html

1. Make Public Gist, get secret, add secret to this repo.

2. Make Workflows to get coverage and make badge(s).

To Do's
==========

..  todolist::

