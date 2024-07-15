"""
Create schema, populate tables, and run a query.
"""
import sqlite3
from dataclasses import dataclass, fields
from pprint import pprint
from typing import Any

def create_sql(table_class: type) -> str:
    table_name = table_class.__name__
    schema = ",\n".join(f"{field.name} STRING" for field in fields(table_class))
    return f"CREATE TABLE {table_name} ({schema})"

def insert_sql(table_class: type, data: dict[str, Any]) -> str:
    cols = ", ".join(f"{field.name}" for field in fields(table_class))
    values = ", ".join(f"'{data[field.name]}'" for field in fields(table_class))
    return f"INSERT INTO {table_class.__name__}({cols}) VALUES({values})"


def build_load_run(schema: list[type], data: dict[str, list[Any]], select: str) -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    for table in schema:
        connection.cursor().execute(create_sql(table))
        connection.commit()
        for row in data[table.__name__]:
            connection.cursor().execute(insert_sql(table, row))
        connection.commit()

    c = connection.cursor()
    result = [dict(row) for row in c.execute(select).fetchall()]
    print(select)
    pprint(result)

def q1():
    @dataclass
    class Names:
        code: str
        name: str

    names_data = [
        {"code": 1, "name": "Life"},
        {"code": 2, "name": "Pi"},
        {"code": 3, "name": "Ee"},
    ]
    query = """
        WITH the_codes(code) as (
            SELECT code FROM names
        )
        SELECT * FROM the_codes
        UNION ALL
        SELECT * FROM the_codes
    """
    build_load_run([Names], {"Names": names_data}, query)

def q2():
    """
    w1 = (
        With(t2=Values(a=lambda cr: 42).union(Select(a=lambda cr: 3.14).from_("t2")))
        .select(a=lambda cr: cr.t2.a)
        .from_("t2")
    )
    """
    query = """
    WITH t2(a) AS (VALUES(42) UNION SELECT 3.14 FROM t2)
    SELECT a
    FROM t2
    """
    build_load_run([], {}, query)

def main():
    # q1()
    q2()

if __name__ == "__main__":
    main()
