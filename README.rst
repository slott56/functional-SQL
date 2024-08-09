###############
functional-SQL
###############

|Python| |ruff-linter| |pyright-checker| |license| |sphinx|

A library to help build SQL-like functionality without the overhead of a database.

See https://slott56.github.io/functional-SQL/_build/html/index.html for the documentation.


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

Yes. The Python is longer. Yes it has ``lambda cr: cr.`` scattered around. The Python produces the same results as the SQL query, using essentially the same algorithm.
You can write Python using the SQL algorithm design pattern.
And without using a database.


..  |Python| image:: https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat&logo=python&logoColor=white
    :target: https://www.python.org

..  |ruff-linter| image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
    :target: https://github.com/astral-sh/ruff

..  |pyright-checker| image:: https://microsoft.github.io/pyright/img/pyright_badge.svg
    :target: https://microsoft.github.io/pyright/

..  |license| image:: https://img.shields.io/badge/License-Apache_2.0-blue.svg
    :target: https://opensource.org/licenses/Apache-2.0

..  |sphinx| image:: https://img.shields.io/badge/Sphinx-000?logo=sphinx&logoColor=fff
    :target: docs
