"""
Test a number of subquery variants.

See https://www.w3resource.com/sql/subqueries/understanding-sql-subqueries.php
for examples.
"""

import sqlite3
from textwrap import dedent
from pprint import pprint
import statistics

import pytest

from funcsql import *


def parse_table(name: str, text: str) -> Table:
    lines = list(filter(None, text.splitlines()))
    header, _, *data_text = lines
    schema = [c.strip() for c in header[:-1].split("|")]
    data = [
        {col: val for col, val in zip(schema, (c.strip() for c in row[:-1].split("|")))}
        for row in data_text
    ]
    return Table(name, data)


@pytest.fixture
def employees():
    table = parse_table(
        "employees",
        dedent(
            """
    employee_id|first_name |last_name  |email   |phone_number      |hire_date |job_id    |salary  |commission_pct|manager_id|department_id|
    -----------+-----------+-----------+--------+------------------+----------+----------+--------+--------------+----------+-------------+
            100|Steven     |King       |SKING   |515.123.4567      |2003-06-17|AD_PRES   |24000.00|          0.00|         0|           90|
            101|Neena      |Kochhar    |NKOCHHAR|515.123.4568      |2005-09-21|AD_VP     |17000.00|          0.00|       100|           90|
            102|Lex        |De Haan    |LDEHAAN |515.123.4569      |2001-01-13|AD_VP     |17000.00|          0.00|       100|           90|
            103|Alexander  |Hunold     |AHUNOLD |590.423.4567      |2006-01-03|IT_PROG   | 9000.00|          0.00|       102|           60|
            104|Bruce      |Ernst      |BERNST  |590.423.4568      |2007-05-21|IT_PROG   | 6000.00|          0.00|       103|           60|
            105|David      |Austin     |DAUSTIN |590.423.4569      |2005-06-25|IT_PROG   | 4800.00|          0.00|       103|           60|
            106|Valli      |Pataballa  |VPATABAL|590.423.4560      |2006-02-05|IT_PROG   | 4800.00|          0.00|       103|           60|
            107|Diana      |Lorentz    |DLORENTZ|590.423.5567      |2007-02-07|IT_PROG   | 4200.00|          0.00|       103|           60|
            108|Nancy      |Greenberg  |NGREENBE|515.124.4569      |2002-08-17|FI_MGR    |12000.00|          0.00|       101|          100|
            109|Daniel     |Faviet     |DFAVIET |515.124.4169      |2002-08-16|FI_ACCOUNT| 9000.00|          0.00|       108|          100|
            110|John       |Chen       |JCHEN   |515.124.4269      |2005-09-28|FI_ACCOUNT| 8200.00|          0.00|       108|          100|
            111|Ismael     |Sciarra    |ISCIARRA|515.124.4369      |2005-09-30|FI_ACCOUNT| 7700.00|          0.00|       108|          100|
            112|Jose Manuel|Urman      |JMURMAN |515.124.4469      |2006-03-07|FI_ACCOUNT| 7800.00|          0.00|       108|          100|
    """
        ),
    )
    return table


@pytest.fixture
def departments():
    table = parse_table(
        "departments",
        dedent(
            """
    department_id|department_name     |manager_id|location_id|
    -------------+--------------------+----------+-----------+
               10|Administration      |       200|       1700|
               20|Marketing           |       201|       1800|
               30|Purchasing          |       114|       1700|
               40|Human Resources     |       203|       2400|
               50|Shipping            |       121|       1500|
               60|IT                  |       103|       1400|
               70|Public Relations    |       204|       2700|
               80|Sales               |       145|       2500|
               90|Executive           |       100|       1700|
              100|Finance             |       108|       1700|
              110|Accounting          |       205|       1700|
              120|Treasury            |         0|       1700|
              130|Corporate Tax       |         0|       1700|
              140|Control And Credit  |         0|       1700|
              150|Shareholder Services|         0|       1700|
              160|Benefits            |         0|       1700|
              170|Manufacturing       |         0|       1700|
              180|Construction        |         0|       1700|
    """
        ),
    )
    return table


def create_sql(table: Table) -> str:
    schema = ",\n".join(f"{name} STRING" for name in table.column_names())
    return f"CREATE TABLE {table.name} ({schema})"


def insert_sql(table: Table, data: dict[str, Any]) -> str:
    cols = ", ".join(f"{name}" for name in data.keys())
    values = ", ".join(f"'{value}'" for value in data.values())
    return f"INSERT INTO {table.name}({cols}) VALUES({values})"


def sqlite_baseline(employees: Table, departments: Table, query: str) -> list[dict[str, Any]]:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.cursor().execute(create_sql(employees))
    connection.cursor().execute(create_sql(departments))
    connection.commit()
    for row in employees.rows:
        connection.cursor().execute(insert_sql(employees, row))
    connection.commit()
    for row in departments.rows:
        connection.cursor().execute(insert_sql(departments, row))
    connection.commit()
    c = connection.cursor()
    result = [dict(row) for row in c.execute(query).fetchall()]
    # print(query)
    # pprint(result)
    return result


def test_subquery_select(employees, departments):
    q1 = """
    SELECT first_name, (SELECT department_name FROM departments WHERE departments.department_id = employees.department_id) AS department_name
    FROM employees;
    """
    expected = sqlite_baseline(employees, departments, q1)
    c1 = Select(
        first_name=lambda c: c.employees.first_name,
        department_name=lambda c: fetch_first_value(
            (
                Select(department_name=lambda sqc: sqc.departments.department_name)
                .from_(departments)
                .where(lambda sqc: sqc.departments.department_id == c.employees.department_id)
            ),
        ),
    ).from_(employees)
    actual = [row._asdict() for row in c1]
    assert actual == expected


def test_subquery_from(employees, departments):
    q2 = """
    SELECT *
    FROM (SELECT first_name, salary FROM employees WHERE salary > 5000) AS "high_salaried";
    """
    expected = sqlite_baseline(employees, departments, q2)
    high_salaried = fetch_table(
        "high_salaried",
        Select(
            first_name=lambda c: c.employees.first_name,
            salary=lambda c: int(float(c.employees.salary)),
        )
        .from_(employees)
        .where(lambda c: float(c.employees.salary) > 5000),
    )
    c2 = Select(STAR).from_(high_salaried)

    actual = [row._asdict() for row in c2]
    assert actual == expected


def test_subquery_where(employees, departments):
    q3 = """
    SELECT first_name
    FROM employees
    WHERE department_id IN (SELECT department_id FROM departments WHERE location_id>1500);
    """
    expected = sqlite_baseline(employees, departments, q3)

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

    actual = [row._asdict() for row in c3]
    assert actual == expected


def test_subquery_having(employees, departments):
    q4 = """
    SELECT department_id, AVG(salary)
    FROM employees
    GROUP BY department_id
    HAVING AVG(salary) > (SELECT AVG(salary) FROM employees);
    """
    expected = sqlite_baseline(employees, departments, q4)

    avg_salary_sq = fetch_first_value(
        Select(
            average=Aggregate(statistics.mean, "salary"), salary=lambda c: float(c.employees.salary)
        ).from_(employees),
    )
    print(f"C4 subquery {avg_salary_sq}")

    c4 = (
        Select(
            department_id=lambda c: int(c.employees.department_id),
            avg_salary=Aggregate(statistics.mean, "salary"),
            salary=lambda c: float(c.employees.salary),
        )
        .from_(employees)
        .group_by("department_id")
        .having(lambda g: g.avg_salary > avg_salary_sq)
    )

    actual = [row._asdict() for row in c4]
    renamed = [
        {name.replace("avg_salary", "AVG(salary)"): value for name, value in row.items()}
        for row in actual
    ]
    assert renamed == expected


def test_subquery_bound(employees, departments):
    q5 = """
    SELECT e.last_name
    FROM employees e
    WHERE EXISTS (
        SELECT * FROM employees b
        WHERE b.employee_id = e.manager_id AND b.last_name = 'King'
    )
    """
    expected = sqlite_baseline(employees, departments, q5)

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

    actual = [row._asdict() for row in c5]
    assert actual == expected
