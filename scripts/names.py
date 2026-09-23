"""Would a list of names fix the errors that names cause?

Capitalised words in mid-sentence are 15% of the words and about half of the errors, so the
obvious next move is a gazetteer: take the names Wikipedia knows and let them overrule the
model. This scores that idea before building it.

The list may only come from the titles of training articles. A dev or test article's title
is part of the text that article is scored on, and Wikidata or a name list scraped from the
live site would carry those titles too.

Every capitalised mid-sentence word of the split is restored once, then each rule is scored
on those answers: how many words it would fix, and how many it would break - the second
number is the one a gazetteer is usually not asked for.

    uv run --group train python scripts/names.py --split dev
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from evaluate import run
from results_page import write_section
from schwa.alphabet import is_foldable, strip_diacritics
from schwa.bundled import default_restorer
from schwa.lexicon import Lexicon
from schwa.tokenize import iter_words, key_of, words_of

DATA = Path("data/processed")
#: The shortest prefix that may be taken for a name when a suffix follows it.
LEAST = 4


def title_names(article_ids: set[str]) -> dict[str, Counter[str]]:
    """Every name-like word of those articles' titles, by typed form."""
    names: dict[str, Counter[str]] = defaultdict(Counter)
    with (DATA / "articles.jsonl").open(encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            if row["id"] not in article_ids:
                continue
            for word in words_of(row["title"]):
                if word[:1].isupper() and any(is_foldable(char) for char in key_of(word)):
                    names[key_of(word)][word] += 1
    return names


def restored_names(split: str, limit: int) -> Counter[tuple[str, str]]:
    """(reference word, what the model wrote) for every capitalised mid-sentence word."""
    references = (DATA / f"{split}.txt").read_text(encoding="utf-8").splitlines()
    if limit:
        references = references[:limit]
    predictions = run(default_restorer(), [strip_diacritics(line) for line in references])

    pairs: Counter[tuple[str, str]] = Counter()
    for reference, prediction in zip(references, predictions, strict=True):
        for index, (start, end) in enumerate(iter_words(reference)):
            expected, produced = reference[start:end], prediction[start:end]
            if index == 0 or not expected[:1].isupper():
                continue
            letters = [char for char in expected if char.isalpha()]
            if len(letters) > 1 and all(char.isupper() for char in letters):
                continue  # words in capitals are a different problem
            pairs[(expected, produced)] += 1
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--split", default="dev", choices=["dev", "test", "web_dev", "web_test"])
    parser.add_argument("--limit", type=int, default=0, help="only the first N sentences")
    args = parser.parse_args()

    training = set((DATA / "train.groups").read_text(encoding="utf-8").split())
    names = title_names(training)
    alone = {key: counts.most_common(1)[0][0] for key, counts in names.items() if len(counts) == 1}
    lexicon = Lexicon.load(DATA / "lexicon.jsonl")
    pairs = restored_names(args.split, args.limit)

    def by_key(key: str, unseen: bool, least_titles: int) -> str | None:
        counts = names.get(key)
        if counts is None or len(counts) > 1 or (unseen and lexicon.total(key) > 0):
            return None
        spelling, seen = counts.most_common(1)[0]
        return spelling if seen >= least_titles else None

    def by_prefix(typed: str, produced: str, unseen: bool) -> str | None:
        """A name in the titles, followed by an Azerbaijani suffix: Muraşko + nun."""
        for length in range(len(typed), LEAST - 1, -1):
            spelling = alone.get(key_of(typed[:length]))
            if spelling is None or len(spelling) != length:
                continue
            if unseen and lexicon.total(key_of(typed[:length])) > 0:
                continue
            return spelling + produced[length:]
        return None

    rules = {
        "the titles spell it one way": lambda word, produced: by_key(key_of(word), False, 1),
        "... and training never saw the word": lambda word, produced: by_key(key_of(word), True, 1),
        "... and it is in two titles or more": lambda word, produced: by_key(
            key_of(word), False, 2
        ),
        "a name in the titles, plus a suffix": lambda word, produced: by_prefix(
            strip_diacritics(word), produced, False
        ),
        "... and training never saw the name": lambda word, produced: by_prefix(
            strip_diacritics(word), produced, True
        ),
    }

    words = sum(pairs.values())
    wrong = sum(count for (expected, produced), count in pairs.items() if expected != produced)
    lines = [
        f"Capitalised mid-sentence words on the {args.split} split: {words:,} of them, "
        f"{wrong:,} restored wrong ({wrong / words:.2%}). Each rule proposes a spelling from "
        f"the names in {len(training):,} training articles' titles "
        f"({len(names):,} typed forms, {len(alone):,} of them spelled one way), and is scored "
        "on the answers above: a word it changes is fixed if the rule is right and the model "
        "was wrong, broken if the model was right and the rule is not.",
        "",
        "| Rule | Words changed | Fixed | Broken | Net |",
        "|---|---|---|---|---|",
    ]
    for name, rule in rules.items():
        fixed = broken = changed = 0
        for (expected, produced), count in pairs.items():
            spelling = rule(expected, produced)
            if spelling is None or spelling == produced:
                continue
            changed += count
            if produced != expected and spelling == expected:
                fixed += count
            elif produced == expected:
                broken += count
        lines.append(f"| {name} | {changed:,} | {fixed:,} | {broken:,} | {fixed - broken:+,} |")
        print(f"{name:<40} changed {changed:>7,} fixed {fixed:>6,} broken {broken:>6,}", flush=True)

    write_section(f"names ({args.split})", "\n".join(lines))
    print("results -> docs/results.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
