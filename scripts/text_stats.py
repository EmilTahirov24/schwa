"""What the text of a split looks like: how long its sentences are, and which letters it uses.

Two sentences in the README rest on these counts: that ə alone is more common than the other
six letters a plain keyboard lacks put together, and that web sentences are no shorter than
Wikipedia's.

    uv run python scripts/text_stats.py --split dev
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from results_page import write_section
from schwa.alphabet import az_lower
from schwa.tokenize import words_of

DATA = Path("data/processed")
MISSING = "əçğıöşü"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", default="dev", choices=["dev", "test", "web_dev", "web_test"])
    args = parser.parse_args()

    path = DATA / f"{args.split}.txt"
    if not path.exists():
        print(f"missing: {path}", file=sys.stderr)
        return 1

    letters: Counter[str] = Counter()
    sentences = words = 0
    with path.open(encoding="utf-8") as source:
        for line in source:
            sentences += 1
            words += len(words_of(line))
            letters.update(char for char in az_lower(line) if char.isalpha())

    total = sum(letters.values())
    missing = sum(letters[char] for char in MISSING)
    others = missing - letters["ə"]
    lines = [
        f"{sentences:,} sentences, {words:,} words: {words / sentences:.1f} words per sentence. "
        f"Letters are counted lower-cased the Azerbaijani way, {total:,} of them.",
        "",
        "| Letter | Share of letters |",
        "|---|---|",
        *(f"| {char} | {count / total:.2%} |" for char, count in letters.most_common(5)),
        "",
        f"The seven letters a plain keyboard lacks make up {missing / total:.1%} of all letters:"
        f" ə alone {letters['ə'] / total:.1%}, the other six together {others / total:.1%}.",
    ]
    write_section(f"text ({args.split})", "\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
