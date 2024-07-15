"""
Functional SQL Demonstration.

We'll work with some trivial data, the Ascombe Quartet.

See https://www.kaggle.com/datasets/carlmcbrideellis/data-anscombes-quartet

The downloaded file is ``Anscombe_quartet_data.csv``,
"""

from pathlib import Path
from csv import DictReader
from statistics import mean, stdev

from funcsql import *


DEFAULT_PATH = Path("tests") / "Anscombe_quartet_data.csv"


def get_series(path: Path = DEFAULT_PATH) -> list[dict[str, str]]:
    """
    Get all four series.

    :param path: source path
    :return: a list of dictionaries with keys "series", "x", and "y".
    """
    with open(path) as source_file:
        rdr = DictReader(source_file)
        return list(rdr)


def restructure(sample_rows: list[dict[str, str]]) -> list[Row]:
    """
    Transform the mish-mash of columns to a series number, and x, y values.

    :param samples: the raw results of the CSV ``DictReader``.
    :return: A list of ``Row`` instances.
    """
    samples = Table("samples", sample_rows)

    q1 = Select(
        series=lambda cr: 1,
        x=lambda cr: float(cr.samples.x123),
        y=lambda cr: float(cr.samples.y1),
    ).from_(samples)
    q2 = Select(
        series=lambda cr: 2,
        x=lambda cr: float(cr.samples.x123),
        y=lambda cr: float(cr.samples.y2),
    ).from_(samples)
    q3 = Select(
        series=lambda cr: 3,
        x=lambda cr: float(cr.samples.x123),
        y=lambda cr: float(cr.samples.y3),
    ).from_(samples)
    q4 = Select(
        series=lambda cr: 4,
        x=lambda cr: float(cr.samples.x4),
        y=lambda cr: float(cr.samples.y4),
    ).from_(samples)

    rows = (
        list(fetch(q1)) + list(fetch(q2))
        + list(fetch(q3)) + list(fetch(q4))
    )

    return rows


def main() -> None:
    data = restructure(get_series())
    anscombe = Table.from_rows("anscombe", data)

    print("Series I")
    query = (
        Select(x=lambda cr: cr.anscombe.x, y=lambda cr: cr.anscombe.y)
        .from_(anscombe)
        .where(lambda cr: cr.anscombe.series == 1)
    )
    for r in fetch(query):
        print(f"{r.x:6.2f}, {r.y:6.2f}")

    print("Means")
    stats_query = (
        Select(
            mean_x=Aggregate(mean, lambda cr: cr.anscombe.x),
            mean_y=Aggregate(mean, lambda cr: cr.anscombe.y)
        )
        .from_(anscombe)
        .group_by(series=lambda cr: cr.anscombe.series)
    )
    for r in fetch(stats_query):
        print(f"{r.series} {r.mean_x:.2f} {r.mean_y:.2f}")

import pytest

def test_main(capsys) -> None:
    main()
    out, err = capsys.readouterr()
    assert err == ""
    assert "1 9.00 7.50" in out
    assert "2 9.00 7.50" in out
    assert "3 9.00 7.50" in out
    assert "4 9.00 7.50" in out

if __name__ == "__main__":
    main()
