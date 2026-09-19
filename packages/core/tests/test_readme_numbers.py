"""Every result table in the docs must say what the last evaluation measured.

Each table is preceded by a comment naming its split, `<!-- results: test -->`, and every
number in it is compared with docs/results.json, which scripts/evaluate.py writes. A number
copied by hand drifts - one CER in the README once disagreed with the results page in its
last digit - and this makes that a failing test instead of a quiet inconsistency.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
DOCUMENTS = [
    ROOT / "README.md",
    ROOT / "docs" / "model_card.md",
    ROOT / "packages" / "core" / "README.md",
]
NUMBERS = ROOT / "docs" / "results.json"
MARKER = re.compile(r"<!-- results: (\w+) -->")

COLUMNS = {
    "Ambiguous word accuracy": ("ambiguous_accuracy", "{:.1%}"),
    "Word accuracy": ("word_accuracy", "{:.1%}"),
    "CER": ("character_error_rate", "{:.2%}"),
    "Sentence accuracy": ("sentence_accuracy", "{:.1%}"),
}


def tables(document: Path) -> Iterator[tuple[str, list[list[str]]]]:
    """Each marked table as its split and its rows of cells, bold markers removed."""
    lines = document.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        match = MARKER.fullmatch(line.strip())
        if not match:
            continue
        rows: list[list[str]] = []
        for row in lines[index + 1 :]:
            if not row.startswith("|"):
                if rows:
                    break
                continue
            rows.append([cell.strip().strip("*") for cell in row.strip().strip("|").split("|")])
        yield match.group(1), rows


@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda path: path.name)
def test_each_document_marks_a_table_for_each_test_split(document: Path):
    assert {split for split, _ in tables(document)} == {"test", "web_test"}


@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda path: path.name)
def test_every_number_in_the_tables_is_the_measured_one(document: Path):
    numbers = json.loads(NUMBERS.read_text(encoding="utf-8"))
    mismatches = []
    for split, rows in tables(document):
        header, _separator, *body = rows
        for cells in body:
            measured = numbers[split]["systems"][cells[0]]
            for column, cell in zip(header[1:], cells[1:], strict=True):
                rate, form = COLUMNS[column]
                if cell != form.format(measured[rate]):
                    mismatches.append(
                        f"{split} / {cells[0]} / {column}: {document.name} says {cell}, "
                        f"measured {form.format(measured[rate])}"
                    )
    assert mismatches == []
