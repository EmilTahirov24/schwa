"""docs/results.md is written by several scripts; none of them may erase another's numbers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "scripts"))

from results_page import write_section  # noqa: E402


def titles(path: Path) -> list[str]:
    return [
        line[4:] for line in path.read_text(encoding="utf-8").splitlines() if line[:4] == "### "
    ]


def test_a_section_replaces_only_its_own_numbers(tmp_path: Path):
    page = tmp_path / "results.md"
    write_section("test", "first run", page)
    write_section("spelling (test)", "typos", page)
    write_section("test", "second run", page)

    text = page.read_text(encoding="utf-8")
    assert "second run" in text
    assert "first run" not in text
    assert "typos" in text


def test_sections_keep_one_order_whichever_script_ran_last(tmp_path: Path):
    page = tmp_path / "results.md"
    for title in ("text (dev)", "errors (web_test)", "web_test", "errors (test)", "dev"):
        write_section(title, "numbers", page)
    assert titles(page) == ["dev", "web_test", "errors (web_test)", "errors (test)", "text (dev)"]
